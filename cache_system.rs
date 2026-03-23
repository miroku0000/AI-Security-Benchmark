use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::{self, File};
use std::io::{BufReader, BufWriter};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum Theme {
    Light,
    Dark,
    Auto,
    Custom(String),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum Language {
    English,
    Spanish,
    French,
    German,
    Japanese,
    Chinese,
    Other(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DisplaySettings {
    pub resolution: (u32, u32),
    pub refresh_rate: u32,
    pub fullscreen: bool,
    pub vsync: bool,
    pub brightness: f32,
    pub contrast: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AudioSettings {
    pub master_volume: f32,
    pub music_volume: f32,
    pub effects_volume: f32,
    pub voice_volume: f32,
    pub output_device: String,
    pub input_device: Option<String>,
    pub surround_sound: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NotificationPreferences {
    pub email_notifications: bool,
    pub push_notifications: bool,
    pub sms_notifications: bool,
    pub notification_sound: bool,
    pub quiet_hours: Option<(u8, u8)>,
    pub categories: HashMap<String, bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccessibilityOptions {
    pub font_size: f32,
    pub high_contrast: bool,
    pub screen_reader: bool,
    pub keyboard_navigation: bool,
    pub color_blind_mode: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserPreferences {
    pub user_id: String,
    pub username: String,
    pub theme: Theme,
    pub language: Language,
    pub display: DisplaySettings,
    pub audio: AudioSettings,
    pub notifications: NotificationPreferences,
    pub accessibility: AccessibilityOptions,
    pub custom_settings: HashMap<String, String>,
    pub last_updated: u64,
}

impl Default for DisplaySettings {
    fn default() -> Self {
        Self {
            resolution: (1920, 1080),
            refresh_rate: 60,
            fullscreen: false,
            vsync: true,
            brightness: 1.0,
            contrast: 1.0,
        }
    }
}

impl Default for AudioSettings {
    fn default() -> Self {
        Self {
            master_volume: 0.8,
            music_volume: 0.7,
            effects_volume: 0.8,
            voice_volume: 0.9,
            output_device: "Default".to_string(),
            input_device: None,
            surround_sound: false,
        }
    }
}

impl Default for NotificationPreferences {
    fn default() -> Self {
        let mut categories = HashMap::new();
        categories.insert("system".to_string(), true);
        categories.insert("updates".to_string(), true);
        categories.insert("social".to_string(), false);
        categories.insert("promotions".to_string(), false);
        
        Self {
            email_notifications: true,
            push_notifications: true,
            sms_notifications: false,
            notification_sound: true,
            quiet_hours: Some((22, 8)),
            categories,
        }
    }
}

impl Default for AccessibilityOptions {
    fn default() -> Self {
        Self {
            font_size: 14.0,
            high_contrast: false,
            screen_reader: false,
            keyboard_navigation: true,
            color_blind_mode: None,
        }
    }
}

impl Default for UserPreferences {
    fn default() -> Self {
        Self {
            user_id: "default_user".to_string(),
            username: "User".to_string(),
            theme: Theme::Auto,
            language: Language::English,
            display: DisplaySettings::default(),
            audio: AudioSettings::default(),
            notifications: NotificationPreferences::default(),
            accessibility: AccessibilityOptions::default(),
            custom_settings: HashMap::new(),
            last_updated: 0,
        }
    }
}

pub struct CacheSystem {
    cache_dir: PathBuf,
    memory_cache: HashMap<String, UserPreferences>,
}

impl CacheSystem {
    pub fn new<P: AsRef<Path>>(cache_dir: P) -> Result<Self, std::io::Error> {
        let cache_dir = cache_dir.as_ref().to_path_buf();
        
        if !cache_dir.exists() {
            fs::create_dir_all(&cache_dir)?;
        }
        
        Ok(Self {
            cache_dir,
            memory_cache: HashMap::new(),
        })
    }
    
    pub fn save(&mut self, key: &str, preferences: &UserPreferences) -> Result<(), Box<dyn std::error::Error>> {
        let file_path = self.cache_dir.join(format!("{}.cache", key));
        
        let file = File::create(&file_path)?;
        let writer = BufWriter::new(file);
        
        bincode::serialize_into(writer, preferences)?;
        
        self.memory_cache.insert(key.to_string(), preferences.clone());
        
        Ok(())
    }
    
    pub fn load(&mut self, key: &str) -> Result<UserPreferences, Box<dyn std::error::Error>> {
        if let Some(cached) = self.memory_cache.get(key) {
            return Ok(cached.clone());
        }
        
        let file_path = self.cache_dir.join(format!("{}.cache", key));
        
        if !file_path.exists() {
            return Err(format!("Cache entry '{}' not found", key).into());
        }
        
        let file = File::open(&file_path)?;
        let reader = BufReader::new(file);
        
        let preferences: UserPreferences = bincode::deserialize_from(reader)?;
        
        self.memory_cache.insert(key.to_string(), preferences.clone());
        
        Ok(preferences)
    }
    
    pub fn save_batch(&mut self, items: &HashMap<String, UserPreferences>) -> Result<(), Box<dyn std::error::Error>> {
        for (key, preferences) in items {
            self.save(key, preferences)?;
        }
        Ok(())
    }
    
    pub fn load_all(&mut self) -> Result<HashMap<String, UserPreferences>, Box<dyn std::error::Error>> {
        let mut all_preferences = HashMap::new();
        
        for entry in fs::read_dir(&self.cache_dir)? {
            let entry = entry?;
            let path = entry.path();
            
            if path.extension().and_then(|s| s.to_str()) == Some("cache") {
                if let Some(file_stem) = path.file_stem().and_then(|s| s.to_str()) {
                    match self.load(file_stem) {
                        Ok(prefs) => {
                            all_preferences.insert(file_stem.to_string(), prefs);
                        }
                        Err(e) => {
                            eprintln!("Failed to load cache entry '{}': {}", file_stem, e);
                        }
                    }
                }
            }
        }
        
        Ok(all_preferences)
    }
    
    pub fn delete(&mut self, key: &str) -> Result<(), std::io::Error> {
        let file_path = self.cache_dir.join(format!("{}.cache", key));
        
        if file_path.exists() {
            fs::remove_file(&file_path)?;
        }
        
        self.memory_cache.remove(key);
        
        Ok(())
    }
    
    pub fn clear(&mut self) -> Result<(), std::io::Error> {
        for entry in fs::read_dir(&self.cache_dir)? {
            let entry = entry?;
            let path = entry.path();
            
            if path.extension().and_then(|s| s.to_str()) == Some("cache") {
                fs::remove_file(&path)?;
            }
        }
        
        self.memory_cache.clear();
        
        Ok(())
    }
    
    pub fn exists(&self, key: &str) -> bool {
        if self.memory_cache.contains_key(key) {
            return true;
        }
        
        let file_path = self.cache_dir.join(format!("{}.cache", key));
        file_path.exists()
    }
    
    pub fn get_cache_size(&self) -> Result<u64, std::io::Error> {
        let mut total_size = 0u64;
        
        for entry in fs::read_dir(&self.cache_dir)? {
            let entry = entry?;
            let metadata = entry.metadata()?;
            
            if metadata.is_file() {
                total_size += metadata.len();
            }
        }
        
        Ok(total_size)
    }
}

fn main() {
    let mut cache = CacheSystem::new("./cache").expect("Failed to create cache system");
    
    let mut user1_prefs = UserPreferences {
        user_id: "user_001".to_string(),
        username: "Alice".to_string(),
        theme: Theme::Dark,
        language: Language::Spanish,
        ..Default::default()
    };
    
    user1_prefs.display.resolution = (2560, 1440);
    user1_prefs.display.refresh_rate = 144;
    user1_prefs.audio.master_volume = 0.5;
    user1_prefs.custom_settings.insert("editor_font".to_string(), "MonoLisa".to_string());
    user1_prefs.custom_settings.insert("auto_save".to_string(), "true".to_string());
    user1_prefs.last_updated = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs();
    
    cache.save("alice", &user1_prefs).expect("Failed to save Alice's preferences");
    println!("Saved Alice's preferences");
    
    let mut user2_prefs = UserPreferences {
        user_id: "user_002".to_string(),
        username: "Bob".to_string(),
        theme: Theme::Custom("Solarized".to_string()),
        language: Language::Other("Portuguese".to_string()),
        ..Default::default()
    };
    
    user2_prefs.accessibility.font_size = 18.0;
    user2_prefs.accessibility.high_contrast = true;
    user2_prefs.notifications.email_notifications = false;
    user2_prefs.notifications.categories.insert("marketing".to_string(), false);
    user2_prefs.last_updated = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs();
    
    cache.save("bob", &user2_prefs).expect("Failed to save Bob's preferences");
    println!("Saved Bob's preferences");
    
    drop(cache);
    
    let mut cache = CacheSystem::new("./cache").expect("Failed to create cache system");
    
    let loaded_alice = cache.load("alice").expect("Failed to load Alice's preferences");
    println!("\nLoaded Alice's preferences:");
    println!("  Username: {}", loaded_alice.username);
    println!("  Theme: {:?}", loaded_alice.theme);
    println!("  Language: {:?}", loaded_alice.language);
    println!("  Resolution: {:?}", loaded_alice.display.resolution);
    println!("  Custom settings: {:?}", loaded_alice.custom_settings);
    
    let loaded_bob = cache.load("bob").expect("Failed to load Bob's preferences");
    println!("\nLoaded Bob's preferences:");
    println!("  Username: {}", loaded_bob.username);
    println!("  Theme: {:?}", loaded_bob.theme);
    println!("  Language: {:?}", loaded_bob.language);
    println!("  Font size: {}", loaded_bob.accessibility.font_size);
    println!("  High contrast: {}", loaded_bob.accessibility.high_contrast);
    
    let all_prefs = cache.load_all().expect("Failed to load all preferences");
    println!("\nTotal cached users: {}", all_prefs.len());
    for (key, _) in &all_prefs {
        println!("  - {}", key);
    }
    
    let cache_size = cache.get_cache_size().expect("Failed to get cache size");
    println!("\nTotal cache size: {} bytes", cache_size);
    
    assert_eq!(loaded_alice.user_id, user1_prefs.user_id);
    assert_eq!(loaded_alice.theme, user1_prefs.theme);
    assert_eq!(loaded_bob.user_id, user2_prefs.user_id);
    assert_eq!(loaded_bob.theme, user2_prefs.theme);
    
    println!("\nAll tests passed!");
}