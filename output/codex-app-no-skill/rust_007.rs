UserPreferences {
        user_id: 1001,
        username: "alice".to_string(),
        theme: Theme::Custom {
            background: "#101820".to_string(),
            foreground: "#F2F2F2".to_string(),
            accent: "#FF6F61".to_string(),
        },
        language: "en-US".to_string(),
        favorites: vec![
            "rust".to_string(),
            "distributed-systems".to_string(),
            "music".to_string(),
        ],
        notification_settings: NotificationSettings {
            enabled: true,
            channels: vec![
                NotificationChannel::Email,
                NotificationChannel::Push,
                NotificationChannel::InApp,
            ],
            quiet_hours: Some((22, 7)),
        },
        privacy_settings: PrivacySettings {
            profile_visibility: PrivacyLevel::FriendsOnly,
            search_engine_indexing: false,
            data_sharing: false,
        },
        editor_settings: EditorSettings {
            font_size: 14,
            tab_width: 4,
            word_wrap: true,
            autosave_seconds: 30,
        },
        feature_flags,
        custom_preferences,
    }
}