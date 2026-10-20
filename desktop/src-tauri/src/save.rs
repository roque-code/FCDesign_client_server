//! Guarda un archivo con el diálogo del sistema.
//!
//! WebView2 (Windows), WebKitGTK (Linux) y WKWebView (macOS) no completan un
//! `<a download>`: en Mac la navegación se cancela si no hay un manejador, y en
//! Windows y Linux el blob no llega a disco. El diálogo nativo sí lo escribe.
//!
//! El diálogo tiene que arrancar en el hilo principal y esta función no puede
//! bloquearlo: si lo hace, el bucle de eventos no pinta el diálogo.

use base64::Engine;
use tauri::AppHandle;
use tauri_plugin_dialog::DialogExt;

const SAVE_ERROR: &str = "No se pudo guardar el archivo.";
const MAX_BYTES: usize = 25 * 1024 * 1024;

#[tauri::command]
pub async fn save_download(
    app: AppHandle,
    filename: String,
    data_base64: String,
) -> Result<bool, String> {
    let bytes = base64::engine::general_purpose::STANDARD
        .decode(data_base64.trim())
        .map_err(|_| SAVE_ERROR.to_string())?;
    if bytes.len() > MAX_BYTES {
        return Err(SAVE_ERROR.to_string());
    }
    let name = safe_name(&filename);
    tauri::async_runtime::spawn_blocking(move || write_chosen(app, name, bytes))
        .await
        .map_err(|_| SAVE_ERROR.to_string())?
}

fn write_chosen(app: AppHandle, name: String, bytes: Vec<u8>) -> Result<bool, String> {
    let mut dialog = app.dialog().file().set_file_name(&name);
    if let Some(ext) = extension(&name) {
        let label: &str = &ext;
        dialog = dialog.add_filter(label, &[label]);
    }
    let Some(chosen) = dialog.blocking_save_file() else {
        return Ok(false);
    };
    let path = chosen.into_path().map_err(|_| SAVE_ERROR.to_string())?;
    if let Some(parent) = path.parent() {
        if !parent.as_os_str().is_empty() {
            std::fs::create_dir_all(parent).map_err(|_| SAVE_ERROR.to_string())?;
        }
    }
    std::fs::write(&path, bytes).map_err(|_| SAVE_ERROR.to_string())?;
    Ok(true)
}

fn safe_name(filename: &str) -> String {
    let base = filename.rsplit(['/', '\\']).next().unwrap_or(filename);
    let cleaned: String = base
        .chars()
        .filter(|ch| !"\\/:*?\"<>|".contains(*ch) && !ch.is_control())
        .take(120)
        .collect();
    let cleaned = cleaned.trim().trim_matches('.').to_string();
    if cleaned.is_empty() {
        "archivo".to_string()
    } else {
        cleaned
    }
}

fn extension(name: &str) -> Option<String> {
    let ext = name.rsplit_once('.')?.1;
    if ext.is_empty() || ext.len() > 8 || !ext.chars().all(|ch| ch.is_ascii_alphanumeric()) {
        None
    } else {
        Some(ext.to_string())
    }
}
