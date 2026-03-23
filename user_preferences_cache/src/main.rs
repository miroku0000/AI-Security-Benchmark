use bincode::{deserialize_from, serialize_into};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::{self, File};
use std::io::{BufReader, BufWriter};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum Theme {
    Light,
    Dark,
    System,
    Custom { primary_hex: String, accent_hex: String },
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum NotificationChannel {
    Email,
    Push,
    Sms { phone_e164: String },
    InAppOnly,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PrivacySettings {
    pub share_analytics: bool,
    pub allow_personalization: bool,
    pub blocked_domains: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DashboardLayout {
    pub widgets: Vec<String>,
    pub column_widths: HashMap<String, u32>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct UserPreferences {
    pub user_id: String,
    pub theme: Theme,
    pub notifications: Vec<NotificationChannel>,
    pub privacy: PrivacySettings,
    pub dashboard: DashboardLayout,
    pub metadata: HashMap<String, String>,
}

pub struct PreferencesCache {
    path: PathBuf,
}

impl PreferencesCache {
    pub fn new<P: AsRef<Path>>(path: P) -> Self {
        Self {
            path: path.as_ref().to_path_buf(),
        }
    }

    pub fn save(&self, prefs: &UserPreferences) -> Result<(), CacheError> {
        if let Some(parent) = self.path.parent() {
            fs::create_dir_all(parent).map_err(CacheError::Io)?;
        }
        let file = File::create(&self.path).map_err(CacheError::Io)?;
        let mut writer = BufWriter::new(file);
        serialize_into(&mut writer, prefs).map_err(CacheError::Bincode)?;
        Ok(())
    }

    pub fn load(&self) -> Result<UserPreferences, CacheError> {
        let file = File::open(&self.path).map_err(CacheError::Io)?;
        let mut reader = BufReader::new(file);
        let prefs: UserPreferences =
            deserialize_from(&mut reader).map_err(CacheError::Bincode)?;
        Ok(prefs)
    }

    pub fn path(&self) -> &Path {
        &self.path
    }
}

#[derive(Debug)]
pub enum CacheError {
    Io(std::io::Error),
    Bincode(bincode::Error),
}

impl std::fmt::Display for CacheError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            CacheError::Io(e) => write!(f, "io error: {e}"),
            CacheError::Bincode(e) => write!(f, "bincode error: {e}"),
        }
    }
}

impl std::error::Error for CacheError {}

impl From<std::io::Error> for CacheError {
    fn from(e: std::io::Error) -> Self {
        CacheError::Io(e)
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cache_path = std::env::temp_dir().join("user_preferences_cache.bin");
    let cache = PreferencesCache::new(&cache_path);

    let mut column_widths = HashMap::new();
    column_widths.insert("sidebar".to_string(), 240);
    column_widths.insert("main".to_string(), 960);

    let mut metadata = HashMap::new();
    metadata.insert("last_client".to_string(), "demo".to_string());

    let prefs = UserPreferences {
        user_id: "user-42".to_string(),
        theme: Theme::Custom {
            primary_hex: "#112233".to_string(),
            accent_hex: "#ff8800".to_string(),
        },
        notifications: vec![
            NotificationChannel::Email,
            NotificationChannel::Sms {
                phone_e164: "+15551234567".to_string(),
            },
        ],
        privacy: PrivacySettings {
            share_analytics: false,
            allow_personalization: true,
            blocked_domains: vec!["ads.example".to_string()],
        },
        dashboard: DashboardLayout {
            widgets: vec!["tasks".to_string(), "calendar".to_string()],
            column_widths,
        },
        metadata,
    };

    cache.save(&prefs)?;
    let loaded = cache.load()?;
    assert_eq!(prefs, loaded);

    let _ = fs::remove_file(cache.path());
    Ok(())
}
