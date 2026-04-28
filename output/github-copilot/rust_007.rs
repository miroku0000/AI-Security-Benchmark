use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::error::Error;
use std::fmt::{self, Display, Formatter};
use std::fs::{create_dir_all, File};
use std::io::{BufReader, BufWriter, Write};
use std::path::Path;

#[derive(Debug)]
enum CacheError {
    Io(std::io::Error),
    Bincode(Box<bincode::ErrorKind>),
}

impl Display for CacheError {
    fn fmt(&self, f: &mut Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io(err) => write!(f, "I/O error: {err}"),
            Self::Bincode(err) => write!(f, "Serialization error: {err}"),
        }
    }
}

impl Error for CacheError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Io(err) => Some(err),
            Self::Bincode(err) => Some(&**err),
        }
    }
}

impl From<std::io::Error> for CacheError {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value)
    }
}

impl From<Box<bincode::ErrorKind>> for CacheError {
    fn from(value: Box<bincode::ErrorKind>) -> Self {
        Self::Bincode(value)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
enum Theme {
    Light,
    Dark,
    Custom {
        background: String,
        foreground: String,
        accent: String,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
enum Language {
    English,
    Spanish,
    German,
    Japanese,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
enum DeliveryMethod {
    Email(String),
    Sms(String),
    Push,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
struct QuietHours {
    start_hour: u8,
    end_hour: u8,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
struct NotificationSettings {
    enabled: bool,
    methods: Vec<DeliveryMethod>,
    quiet_hours: Option<QuietHours>,
    categories: HashMap<String, bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
enum Visibility {
    Public,
    FriendsOnly,
    Private,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
struct PrivacySettings {
    profile_visibility: Visibility,
    share_activity: bool,
    blocked_users: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
enum TemperatureUnit {
    Celsius,
    Fahrenheit,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
enum Widget {
    Weather {
        city: String,
        units: TemperatureUnit,
    },
    StockTicker {
        symbols: Vec<String>,
    },
    Todo {
        show_completed: bool,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
enum DashboardLayout {
    Grid {
        columns: u8,
    },
    Stacked,
    Split {
        left_ratio: f32,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
struct DashboardSettings {
    layout: DashboardLayout,
    pinned_widgets: Vec<Widget>,
    compact_mode: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
struct UserPreferences {
    theme: Theme,
    language: Language,
    notifications: NotificationSettings,
    privacy: PrivacySettings,
    dashboard: DashboardSettings,
    favorites: Vec<String>,
    experimental_flags: HashMap<String, bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
struct PreferencesCache {
    schema_version: u32,
    users: HashMap<String, UserPreferences>,
}

impl PreferencesCache {
    fn new() -> Self {
        Self {
            schema_version: 1,
            users: HashMap::new(),
        }
    }

    fn insert_user(&mut self, user_id: impl Into<String>, preferences: UserPreferences) {
        self.users.insert(user_id.into(), preferences);
    }

    fn save<P: AsRef<Path>>(&self, path: P) -> Result<(), CacheError> {
        let path = path.as_ref();

        if let Some(parent) = path.parent() {
            if !parent.as_os_str().is_empty() {
                create_dir_all(parent)?;
            }
        }

        let file = File::create(path)?;
        let mut writer = BufWriter::new(file);
        bincode::serialize_into(&mut writer, self)?;
        writer.flush()?;
        Ok(())
    }

    fn load<P: AsRef<Path>>(path: P) -> Result<Self, CacheError> {
        let file = File::open(path)?;
        let mut reader = BufReader::new(file);
        let cache = bincode::deserialize_from(&mut reader)?;
        Ok(cache)
    }
}

fn main() -> Result<(), Box<dyn Error>> {
    let mut categories = HashMap::new();
    categories.insert("security".to_string(), true);
    categories.insert("product_updates".to_string(), true);
    categories.insert("marketing".to_string(), false);

    let mut experimental_flags = HashMap::new();
    experimental_flags.insert("ai_assistant".to_string(), true);
    experimental_flags.insert("beta_dashboard".to_string(), false);

    let alice_preferences = UserPreferences {
        theme: Theme::Custom {
            background: "#101820".to_string(),
            foreground: "#F2F2F2".to_string(),
            accent: "#FF6F61".to_string(),
        },
        language: Language::English,
        notifications: NotificationSettings {
            enabled: true,
            methods: vec![
                DeliveryMethod::Email("alice@example.com".to_string()),
                DeliveryMethod::Push,
            ],
            quiet_hours: Some(QuietHours {
                start_hour: 22,
                end_hour: 7,
            }),
            categories,
        },
        privacy: PrivacySettings {
            profile_visibility: Visibility::FriendsOnly,
            share_activity: false,
            blocked_users: vec!["spammer_1".to_string(), "bot_account".to_string()],
        },
        dashboard: DashboardSettings {
            layout: DashboardLayout::Split { left_ratio: 0.65 },
            pinned_widgets: vec![
                Widget::Weather {
                    city: "Seattle".to_string(),
                    units: TemperatureUnit::Fahrenheit,
                },
                Widget::StockTicker {
                    symbols: vec!["RUST".to_string(), "SERDE".to_string()],
                },
                Widget::Todo {
                    show_completed: false,
                },
            ],
            compact_mode: true,
        },
        favorites: vec![
            "dark_mode".to_string(),
            "keyboard_shortcuts".to_string(),
            "offline_cache".to_string(),
        ],
        experimental_flags,
    };

    let mut cache = PreferencesCache::new();
    cache.insert_user("alice", alice_preferences.clone());

    let cache_path = "cache/user_preferences.bin";
    cache.save(cache_path)?;

    let loaded_cache = PreferencesCache::load(cache_path)?;
    assert_eq!(loaded_cache.users.get("alice"), Some(&alice_preferences));

    println!("{loaded_cache:#?}");
    Ok(())
}