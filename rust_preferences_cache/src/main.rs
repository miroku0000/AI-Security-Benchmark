use serde::{Deserialize, Serialize};
use std::fs::{self, File};
use std::io::{BufReader, BufWriter};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum Theme {
    Light,
    Dark,
    System,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum DigestFrequency {
    Daily,
    Weekly,
    Custom(String),
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NotificationPrefs {
    pub email: bool,
    pub push: bool,
    pub digest: Option<DigestFrequency>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PrivacyPrefs {
    pub analytics: bool,
    pub share_usage: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct UserPreferences {
    pub user_id: String,
    pub theme: Theme,
    pub notifications: NotificationPrefs,
    pub privacy: PrivacyPrefs,
    pub tags: Vec<String>,
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

    pub fn save(&self, prefs: &UserPreferences) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        if let Some(parent) = self.path.parent() {
            fs::create_dir_all(parent)?;
        }
        let file = File::create(&self.path)?;
        let writer = BufWriter::new(file);
        bincode::serialize_into(writer, prefs)?;
        Ok(())
    }

    pub fn load(&self) -> Result<UserPreferences, Box<dyn std::error::Error + Send + Sync>> {
        let file = File::open(&self.path)?;
        let reader = BufReader::new(file);
        let prefs: UserPreferences = bincode::deserialize_from(reader)?;
        Ok(prefs)
    }
}

fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let prefs = UserPreferences {
        user_id: "user-42".into(),
        theme: Theme::Dark,
        notifications: NotificationPrefs {
            email: true,
            push: false,
            digest: Some(DigestFrequency::Weekly),
        },
        privacy: PrivacyPrefs {
            analytics: false,
            share_usage: true,
        },
        tags: vec!["beta".into(), "power-user".into()],
    };

    let cache_path = std::env::temp_dir().join("user_preferences_cache_demo.bin");
    let cache = PreferencesCache::new(&cache_path);
    cache.save(&prefs)?;
    let loaded = cache.load()?;
    assert_eq!(prefs, loaded);
    Ok(())
}
