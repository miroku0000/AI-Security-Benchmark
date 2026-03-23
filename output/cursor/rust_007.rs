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