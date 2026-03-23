use std::env;
use std::path::PathBuf;

use enterprise_xml_config::parse_enterprise_config_xml;

fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let path: PathBuf = env::args()
        .nth(1)
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("config.xml"));
    let base = path
        .parent()
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."));
    let data = std::fs::read(&path)?;
    let map = parse_enterprise_config_xml(&data, &base)?;
    for (k, v) in map {
        println!("{k}={v}");
    }
    Ok(())
}
