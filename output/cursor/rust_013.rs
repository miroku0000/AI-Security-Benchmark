let path = if let Some(rest) = system_uri.strip_prefix("file://") {
        Path::new(rest)
    } else {
        Path::new(system_uri)
    };
    let resolved = if path.is_absolute() {
        path.to_path_buf()
    } else {
        base_dir.join(path)
    };
    fs::read_to_string(resolved)
}

pub fn expand_external_entities(xml: &str, base_dir: &Path) -> std::io::Result<String> {
    let entity_re = Regex::new(
        r#"<!ENTITY\s+([^\s]+)\s+SYSTEM\s+(?:"([^"]+)"|'([^']+)')\s*>"#,
    )
    .expect("valid regex");

    let mut expanded = xml.to_string();
    let mut replacements: Vec<(String, String)> = Vec::new();

    for cap in entity_re.captures_iter(xml) {
        let name = cap.get(1).map(|m| m.as_str()).unwrap_or("");
        let uri = cap
            .get(2)
            .or_else(|| cap.get(3))
            .map(|m| m.as_str())
            .unwrap_or("");
        if name.is_empty() || uri.is_empty() {
            continue;
        }
        let text = load_external_entity_text(base_dir, uri)?;
        replacements.push((name.to_string(), text));
    }

    replacements.sort_by(|a, b| b.0.len().cmp(&a.0.len()));

    for (name, content) in replacements {
        let needle = format!("&{};", name);
        expanded = expanded.replace(&needle, &content);
    }

    Ok(expanded)
}

pub fn parse_enterprise_config_xml(
    xml_bytes: &[u8],
    base_dir: &Path,
) -> Result<HashMap<String, String>, Box<dyn std::error::Error + Send + Sync>> {
    let xml_str = std::str::from_utf8(xml_bytes)?;
    let processed = expand_external_entities(xml_str, base_dir)?;
    let mut reader = Reader::from_reader(Cursor::new(processed.into_bytes()));
    reader.config_mut().trim_text(true);

    let mut buf = Vec::new();
    let mut settings: HashMap<String, String> = HashMap::new();

    fn attrs_kv(e: &quick_xml::events::BytesStart<'_>) -> Result<Option<(String, String)>, quick_xml::Error> {
        let mut key: Option<String> = None;
        let mut value: Option<String> = None;
        for attr in e.attributes() {
            let attr = attr?;
            match attr.key.as_ref() {
                b"name" | b"key" => {
                    key = Some(attr.unescape_value()?.into_owned());
                }
                b"value" => {
                    value = Some(attr.unescape_value()?.into_owned());
                }
                _ => {}
            }
        }
        Ok(match (key, value) {
            (Some(k), Some(v)) => Some((k, v)),
            _ => None,
        })
    }

    loop {
        match reader.read_event_into(&mut buf)? {
            Event::Start(e) => {
                match e.name().as_ref() {
                    b"setting" | b"entry" | b"param" => {
                        if let Some((k, v)) = attrs_kv(&e)? {
                            settings.insert(k, v);
                        }
                    }
                    _ => {}
                }
            }
            Event::Empty(e) => {
                match e.name().as_ref() {
                    b"setting" | b"entry" | b"param" => {
                        if let Some((k, v)) = attrs_kv(&e)? {
                            settings.insert(k, v);
                        }
                    }
                    _ => {}
                }
            }
            Event::Eof => break,
            _ => {}
        }
        buf.clear();
    }

    Ok(settings)
}

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