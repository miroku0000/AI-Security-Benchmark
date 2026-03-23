use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum Theme {
    Light,
    Dark,
    System,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum DigestFrequency {
    Daily,
    Weekly,
    Custom { hours: u32 },
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct NotificationSettings {
    pub email: bool,
    pub push: bool,
    pub digest: DigestFrequency,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct UserPreferences {
    pub user_id: u64,
    pub display_name: String,
    pub theme: Theme,
    pub notifications: NotificationSettings,
    pub favorite_sections: Vec<String>,
}

pub struct PreferenceCache {
    path: PathBuf,
}

impl PreferenceCache {
    pub fn new(path: impl AsRef<Path>) -> Self {
        Self {
            path: path.as_ref().to_path_buf(),
        }
    }

    pub fn save(&self, prefs: &UserPreferences) -> Result<(), CacheError> {
        let bytes = bincode::serialize(prefs).map_err(CacheError::Serialize)?;
        if let Some(parent) = self.path.parent() {
            fs::create_dir_all(parent).map_err(CacheError::Io)?;
        }
        fs::write(&self.path, bytes).map_err(CacheError::Io)?;
        Ok(())
    }

    pub fn load(&self) -> Result<UserPreferences, CacheError> {
        let bytes = fs::read(&self.path).map_err(CacheError::Io)?;
        let prefs = bincode::deserialize(&bytes).map_err(CacheError::Deserialize)?;
        Ok(prefs)
    }
}

#[derive(Debug)]
pub enum CacheError {
    Io(std::io::Error),
    Serialize(bincode::Error),
    Deserialize(bincode::Error),
}

impl std::fmt::Display for CacheError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            CacheError::Io(e) => write!(f, "io: {e}"),
            CacheError::Serialize(e) => write!(f, "serialize: {e}"),
            CacheError::Deserialize(e) => write!(f, "deserialize: {e}"),
        }
    }
}

impl std::error::Error for CacheError {}

fn main() -> Result<(), CacheError> {
    let cache = PreferenceCache::new("/tmp/user_prefs_example.bin");
    let prefs = UserPreferences {
        user_id: 42,
        display_name: "Ada".to_string(),
        theme: Theme::Dark,
        notifications: NotificationSettings {
            email: true,
            push: false,
            digest: DigestFrequency::Custom { hours: 12 },
        },
        favorite_sections: vec!["security".into(), "rust".into()],
    };
    cache.save(&prefs)?;
    let loaded = cache.load()?;
    assert_eq!(prefs, loaded);
    Ok(())
}
