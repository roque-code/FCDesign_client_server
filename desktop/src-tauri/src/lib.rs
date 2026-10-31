mod save;
mod update;

use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;

use tauri::Manager;

struct Bridge {
    origin: String,
    token: String,
    child: Mutex<Child>,
}

#[derive(serde::Deserialize)]
struct Announcement {
    origin: String,
    token: String,
}

#[derive(serde::Deserialize, serde::Serialize)]
struct ProxyBody {
    status: u16,
    body: String,
    csrf: String,
}

#[tauri::command]
fn server_fetch(
    bridge: tauri::State<Bridge>,
    path: String,
    method: String,
    body: Option<String>,
    headers: std::collections::HashMap<String, String>,
) -> Result<ProxyBody, String> {
    if !path.starts_with("/api/") {
        return Err("La ruta no es de la API.".into());
    }
    let endpoint = format!("{}/local/v1/proxy", bridge.origin);
    let sent = ureq::post(&endpoint)
        .set("Authorization", &format!("Bearer {}", bridge.token))
        .set("Content-Type", "application/json")
        .send_json(serde_json::json!({
            "path": path,
            "method": method,
            "body": body,
            "headers": headers,
        }));
    match sent {
        Ok(response) => response.into_json().map_err(|error| error.to_string()),
        // El intérprete local responde con error cuando no alcanza el servidor; su mensaje llega a la ventana.
        Err(ureq::Error::Status(status, response)) => Ok(ProxyBody {
            status,
            body: response.into_string().unwrap_or_default(),
            csrf: String::new(),
        }),
        Err(error) => Err(error.to_string()),
    }
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_deep_link::init())
        .setup(|app| {
            let bridge = start_host().map_err(std::io::Error::other)?;
            let script = init_script(&bridge.origin, &bridge.token);
            let window = tauri::WebviewWindowBuilder::new(
                app,
                "main",
                tauri::WebviewUrl::App("index.html".into()),
            )
            .title("Aulivana-FCDdesign")
            .inner_size(1280.0, 800.0)
            .initialization_script(&script)
            .build()?;
            let handle = app.handle().clone();
            let _ = window;
            app.manage(bridge);
            update::spawn();
            {
                use tauri_plugin_deep_link::DeepLinkExt;
                let urls = handle.deep_link().get_current().ok().flatten().unwrap_or_default();
                if let Some(url) = urls.first() {
                    remember_launch(&handle, url.as_str());
                }
                let launch_handle = handle.clone();
                handle.deep_link().on_open_url(move |event| {
                    if let Some(url) = event.urls().first() {
                        remember_launch(&launch_handle, url.as_str());
                    }
                });
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![server_fetch, save::save_download])
        .build(tauri::generate_context!())
        .expect("No se pudo abrir Aulivana-FCDdesign")
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                if let Some(bridge) = app.try_state::<Bridge>() {
                    if let Ok(mut child) = bridge.child.lock() {
                        let _ = child.kill();
                    }
                }
            }
        });
}

fn remember_launch(app: &tauri::AppHandle, url: &str) {
    let Some(window) = app.get_webview_window("main") else {
        return;
    };
    let quoted = serde_json::to_string(url).unwrap_or_else(|_| "\"\"".into());
    let _ = window.eval(&format!(
        "window.__TRAZA_LAUNCH__ = {quoted}; window.dispatchEvent(new Event('traza-launch'));"
    ));
}

fn init_script(origin: &str, token: &str) -> String {
    let origin = serde_json::to_string(origin).unwrap_or_else(|_| "\"\"".into());
    let token = serde_json::to_string(token).unwrap_or_else(|_| "\"\"".into());
    let proxy = if cfg!(debug_assertions) { "false" } else { "true" };
    format!(
        "window.__TRAZA_LOCAL__ = {{ origin: {origin}, token: {token} }}; window.__TRAZA_DESKTOP_PROXY__ = {proxy};"
    )
}

fn start_host() -> Result<Bridge, String> {
    let token = random_token();
    let api = std::env::var("TRAZA_API_ORIGIN")
        .ok()
        .filter(|value| !value.trim().is_empty())
        .unwrap_or_else(|| "https://fcdesign.aulivana.com".into());
    let mut command = host_command()?;
    if std::env::var("TRAZA_RUNTIME_MANIFEST")
        .ok()
        .filter(|value| !value.is_empty())
        .is_none()
    {
        command.env(
            "TRAZA_RUNTIME_MANIFEST",
            format!("{}/runtimes/manifest.json", api.trim_end_matches('/')),
        );
    }
    command
        .arg("--host")
        .arg("127.0.0.1")
        .arg("--port")
        .arg("0")
        .arg("--token")
        .arg(&token)
        .arg("--api")
        .arg(&api)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit());
    let mut child = command.spawn().map_err(|error| error.to_string())?;
    let stdout = child.stdout.take().ok_or("El intérprete no anunció su puerto.")?;
    let mut reader = BufReader::new(stdout);
    let mut line = String::new();
    let announced = wait_line(&mut reader, &mut line, Duration::from_secs(8))?;
    let announcement: Announcement = serde_json::from_str(announced).map_err(|error| error.to_string())?;
    Ok(Bridge {
        origin: announcement.origin,
        token: announcement.token,
        child: Mutex::new(child),
    })
}

fn wait_line<'a>(
    reader: &mut BufReader<impl std::io::Read>,
    line: &'a mut String,
    _limit: Duration,
) -> Result<&'a str, String> {
    line.clear();
    reader.read_line(line).map_err(|error| error.to_string())?;
    if line.is_empty() {
        return Err("El intérprete local se cerró antes de anunciar el puerto.".into());
    }
    Ok(line.trim())
}

fn host_command() -> Result<Command, String> {
    if let Some(path) = sidecar_path() {
        return Ok(Command::new(path));
    }
    let root = repo_root();
    let mut command = Command::new(if cfg!(windows) { "python" } else { "python3" });
    command.arg("-m").arg("local_host").current_dir(root);
    Ok(command)
}

fn sidecar_path() -> Option<PathBuf> {
    let exe = std::env::current_exe().ok()?;
    let dir = exe.parent()?;
    let suffix = if cfg!(windows) { ".exe" } else { "" };
    let bundled = dir.join(format!("traza-host{suffix}"));
    if bundled.is_file() {
        return Some(bundled);
    }
    let named = dir.join(format!("traza-host-{}{suffix}", env!("TRAZA_HOST_TRIPLE")));
    named.is_file().then_some(named)
}

fn repo_root() -> PathBuf {
    if let Ok(root) = std::env::var("TRAZA_ROOT") {
        return PathBuf::from(root);
    }
    let cwd = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    if cwd.join("language_core").is_dir() {
        return cwd;
    }
    let parent = cwd.join("../..");
    if parent.join("language_core").is_dir() {
        return parent;
    }
    cwd
}

fn random_token() -> String {
    let mut bytes = [0u8; 24];
    getrandom::getrandom(&mut bytes).expect("entropía");
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 0xf) as usize] as char);
    }
    out
}
