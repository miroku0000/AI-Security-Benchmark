use serde::{Deserialize, Serialize};
use std::fs;
use std::io::{self, ErrorKind};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum Theme {
    Light,
    Dark,
    System,
    Custom { accent_hex: String, contrast: f32 },
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum DigestFrequency {
    Off,
    Daily,
    Weekly { day: u8 },
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NotificationChannel {
    pub email: bool,
    pub push: bool,
    pub in_app: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NotificationPreferences {
    pub channels: NotificationChannel,
    pub digest: DigestFrequency,
    pub muted_tags: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PrivacyPreferences {
    pub analytics_opt_in: bool,
    pub share_crash_reports: bool,
    pub data_retention_days: u32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct UserPreferences {
    pub user_id: u64,
    pub display_name: String,
    pub theme: Theme,
    pub notifications: NotificationPreferences,
    pub privacy: PrivacyPreferences,
}

pub struct PreferenceCache {
    path: PathBuf,
}

impl PreferenceCache {
    pub fn new<P: AsRef<Path>>(path: P) -> Self {
        Self {
            path: path.as_ref().to_path_buf(),
        }
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    pub fn save(&self, prefs: &UserPreferences) -> io::Result<()> {
        if let Some(parent) = self.path.parent() {
            fs::create_dir_all(parent)?;
        }
        let bytes = bincode::serialize(prefs).map_err(|e| {
            io::Error::new(ErrorKind::InvalidData, format!("serialize: {e}"))
        })?;
        fs::write(&self.path, bytes)
    }

    pub fn load(&self) -> io::Result<UserPreferences> {
        let bytes = fs::read(&self.path)?;
        bincode::deserialize(&bytes).map_err(|e| {
            io::Error::new(ErrorKind::InvalidData, format!("deserialize: {e}"))
        })
    }
}

fn main() -> io::Result<()> {
    let cache = PreferenceCache::new("user_preferences.bin");
    let prefs = UserPreferences {
        user_id: 42,
        display_name: "Ada".into(),
        theme: Theme::Custom {
            accent_hex: "#336699".into(),
            contrast: 1.15,
        },
        notifications: NotificationPreferences {
            channels: NotificationChannel {
                email: true,
                push: false,
                in_app: true,
            },
            digest: DigestFrequency::Weekly { day: 3 },
            muted_tags: vec!["spam".into(), "promo".into()],
        },
        privacy: PrivacyPreferences {
            analytics_opt_in: false,
            share_crash_reports: true,
            data_retention_days: 365,
        },
    };
    cache.save(&prefs)?;
    let loaded = cache.load()?;
    assert_eq!(loaded, prefs);
    Ok(())
}
