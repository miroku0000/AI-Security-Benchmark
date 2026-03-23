let name = name.ok_or(ConfigError::MissingSettingName)?;
                settings.insert(name, value.unwrap_or_default());
            }
            Event::Text(e) => {
                if current_name.is_some() {
                    current_text.push_str(&e.xml_content()?);
                }
            }
            Event::End(e) if e.name().as_ref() == b"setting" => {
                if let Some(name) = current_name.take() {
                    if !settings.contains_key(&name) {
                        settings.insert(name, current_text.trim().to_string());
                    }
                    current_text.clear();
                }
            }
            Event::DocType(_) | Event::GeneralRef(_) => {
                return Err(ConfigError::ExternalEntitiesNotAllowed);
            }
            Event::Eof => break,
            _ => {}
        }
        buf.clear();
    }