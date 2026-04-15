fn main() {
    cc::Build::new()
        .file("c/legacy.c")
        .warnings(true)
        .compile("legacy");
    println!("cargo:rerun-if-changed=c/legacy.c");
}
