use serde::{Deserialize, Serialize};
use std::fs;
use std::io::{self, Read, Write};
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum Theme {
    Light,
    Dark,
    Custom { name: String, accent_rgb: (u8, u8, u8) },
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct NotificationPreferences {
    pub email: bool,
    pub push: bool,
    pub frequency: NotificationFrequency,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum NotificationFrequency {
    Immediate,
    Daily { hour_utc: u8 },
    Weekly(u32),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PrivacySettings {
    pub share_analytics: bool,
    pub data_retention_days: Option<u32>,
    pub allowed_regions: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct EditorPreferences {
    pub font_family: String,
    pub font_size_pt: f32,
    pub keymap: Keymap,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum Keymap {
    Default,
    Vim { leader: char },
    Emacs,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct UserPreferences {
    pub user_id: String,
    pub theme: Theme,
    pub notifications: NotificationPreferences,
    pub privacy: PrivacySettings,
    pub editor: EditorPreferences,
    pub tags: Vec<String>,
}

pub struct PreferencesCache<P: AsRef<Path>> {
    path: P,
}

impl<P: AsRef<Path>> PreferencesCache<P> {
    pub fn new(path: P) -> Self {
        Self { path }
    }

    pub fn save(&self, prefs: &UserPreferences) -> io::Result<()> {
        let encoded = bincode::serialize(prefs)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
        let path = self.path.as_ref();
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        let mut file = fs::File::create(path)?;
        file.write_all(&encoded)?;
        Ok(())
    }

    pub fn load(&self) -> io::Result<UserPreferences> {
        let mut file = fs::File::open(self.path.as_ref())?;
        let mut buf = Vec::new();
        file.read_to_end(&mut buf)?;
        bincode::deserialize(&buf)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))
    }
}

pub fn save_preferences<P: AsRef<Path>>(path: P, prefs: &UserPreferences) -> io::Result<()> {
    PreferencesCache::new(path).save(prefs)
}

pub fn load_preferences<P: AsRef<Path>>(path: P) -> io::Result<UserPreferences> {
    PreferencesCache::new(path).load()
}

fn main() -> io::Result<()> {
    let path = "user_prefs.cache";
    let prefs = UserPreferences {
        user_id: "alice".to_string(),
        theme: Theme::Custom {
            name: "midnight".to_string(),
            accent_rgb: (94, 129, 172),
        },
        notifications: NotificationPreferences {
            email: true,
            push: false,
            frequency: NotificationFrequency::Daily { hour_utc: 8 },
        },
        privacy: PrivacySettings {
            share_analytics: false,
            data_retention_days: Some(90),
            allowed_regions: vec!["EU".to_string(), "US".to_string()],
        },
        editor: EditorPreferences {
            font_family: "JetBrains Mono".to_string(),
            font_size_pt: 12.5,
            keymap: Keymap::Vim { leader: ' ' },
        },
        tags: vec!["rust".to_string(), "serde".to_string()],
    };
    save_preferences(path, &prefs)?;
    let loaded = load_preferences(path)?;
    assert_eq!(prefs, loaded);
    Ok(())
}
