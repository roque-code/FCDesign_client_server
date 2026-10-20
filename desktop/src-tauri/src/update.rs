// Descarga un paquete más nuevo sin tocar los archivos del usuario.
// Si no hay TRAZA_UPDATE_URL, no hace nada. El directorio de datos de la
// aplicación no se borra: solo se sustituye el paquete de la aplicación.

use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};

#[derive(serde::Deserialize)]
struct Manifest {
    version: String,
    url: String,
}

pub fn spawn() {
    let Ok(url) = std::env::var("TRAZA_UPDATE_URL") else {
        return;
    };
    if url.is_empty() {
        return;
    }
    std::thread::spawn(move || {
        if let Err(error) = check(&url) {
            eprintln!("Aulivana-FCDdesign: la actualización no se aplicó: {error}");
        }
    });
}

fn check(url: &str) -> Result<(), String> {
    let response = ureq::get(url)
        .call()
        .map_err(|error| error.to_string())?;
    let manifest: Manifest = response.into_json().map_err(|error| error.to_string())?;
    if !newer(&manifest.version, env!("CARGO_PKG_VERSION")) {
        return Ok(());
    }
    let bytes = download(&manifest.url)?;
    install(&bytes)
}

fn newer(candidate: &str, current: &str) -> bool {
    let left = parts(candidate);
    let right = parts(current);
    left > right
}

fn parts(version: &str) -> Vec<u64> {
    version
        .split(|ch: char| !ch.is_ascii_digit())
        .filter(|piece| !piece.is_empty())
        .filter_map(|piece| piece.parse().ok())
        .collect()
}

fn download(url: &str) -> Result<Vec<u8>, String> {
    let response = ureq::get(url).call().map_err(|error| error.to_string())?;
    let mut bytes = Vec::new();
    response
        .into_reader()
        .take(512 * 1024 * 1024)
        .read_to_end(&mut bytes)
        .map_err(|error| error.to_string())?;
    Ok(bytes)
}

fn install(bytes: &[u8]) -> Result<(), String> {
    let exe = std::env::current_exe().map_err(|error| error.to_string())?;
    let folder = std::env::temp_dir().join("Aulivana-FCDdesign-update");
    fs::create_dir_all(&folder).map_err(|error| error.to_string())?;
    let staged = folder.join("paquete.bin");
    fs::write(&staged, bytes).map_err(|error| error.to_string())?;
    if exe.is_file() && app_bundle(&exe).is_none() {
        let backup = exe.with_extension("anterior");
        let _ = fs::rename(&exe, &backup);
        fs::rename(&staged, &exe).map_err(|error| error.to_string())?;
        let _ = fs::remove_file(&backup);
        return Ok(());
    }
    eprintln!(
        "Aulivana-FCDdesign: paquete nuevo en {}. No se tocó el directorio de datos del usuario.",
        staged.display()
    );
    Ok(())
}

fn app_bundle(exe: &Path) -> Option<PathBuf> {
    exe.ancestors().find(|path| path.extension().is_some_and(|ext| ext == "app")).map(Path::to_path_buf)
}
