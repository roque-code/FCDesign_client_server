fn main() {
    let target = std::env::var("TARGET").unwrap_or_default();
    println!("cargo:rustc-env=TRAZA_HOST_TRIPLE={target}");
    tauri_build::build();
}
