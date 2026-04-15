use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Theme {
    Light,
    Dark,
    Auto,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Language {
    English,
    Spanish,
    French,
    German,
    Japanese,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NotificationSettings {
    pub email: bool,
    pub push: bool,
    pub sms: bool,
    pub frequency: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PrivacySettings {
    pub profile_visible: bool,
    pub share_data: bool,
    pub analytics_enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DisplaySettings {
    pub theme: Theme,
    pub font_size: u32,
    pub compact_mode: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserPreferences {
    pub user_id: String,
    pub username: String,
    pub language: Language,
    pub display: DisplaySettings,
    pub notifications: NotificationSettings,
    pub privacy: PrivacySettings,
    pub tags: Vec<String>,
}

pub struct PreferencesCache {
    cache_path: String,
}

impl PreferencesCache {
    pub fn new(cache_path: String) -> Self {
        PreferencesCache { cache_path }
    }

    pub fn save(&self, preferences: &UserPreferences) -> Result<(), Box<dyn std::error::Error>> {
        let encoded = bincode::serialize(preferences)?;
        fs::write(&self.cache_path, encoded)?;
        Ok(())
    }

    pub fn load(&self) -> Result<UserPreferences, Box<dyn std::error::Error>> {
        let data = fs::read(&self.cache_path)?;
        let preferences = bincode::deserialize(&data)?;
        Ok(preferences)
    }

    pub fn exists(&self) -> bool {
        Path::new(&self.cache_path).exists()
    }

    pub fn clear(&self) -> Result<(), Box<dyn std::error::Error>> {
        if self.exists() {
            fs::remove_file(&self.cache_path)?;
        }
        Ok(())
    }
}

fn main() {
    let cache = PreferencesCache::new("user_preferences.cache".to_string());

    let preferences = UserPreferences {
        user_id: "user123".to_string(),
        username: "john_doe".to_string(),
        language: Language::English,
        display: DisplaySettings {
            theme: Theme::Dark,
            font_size: 14,
            compact_mode: false,
        },
        notifications: NotificationSettings {
            email: true,
            push: true,
            sms: false,
            frequency: "daily".to_string(),
        },
        privacy: PrivacySettings {
            profile_visible: true,
            share_data: false,
            analytics_enabled: true,
        },
        tags: vec![
            "developer".to_string(),
            "rust".to_string(),
            "backend".to_string(),
        ],
    };

    match cache.save(&preferences) {
        Ok(_) => println!("Preferences saved successfully"),
        Err(e) => eprintln!("Error saving preferences: {}", e),
    }

    match cache.load() {
        Ok(loaded_prefs) => {
            println!("Loaded preferences for user: {}", loaded_prefs.username);
            println!("Theme: {:?}", loaded_prefs.display.theme);
            println!("Language: {:?}", loaded_prefs.language);
            println!("Email notifications: {}", loaded_prefs.notifications.email);
            println!("Tags: {:?}", loaded_prefs.tags);
        }
        Err(e) => eprintln!("Error loading preferences: {}", e),
    }
}