UserPreferences {
        user_id: 42,
        username: "randy".to_string(),
        startup_view: StartupView::SecurityDashboard,
        display: DisplayPreferences {
            theme: Theme::Custom {
                background_hex: "#101820".to_string(),
                foreground_hex: "#F2F2F2".to_string(),
                accent_hex: "#00C2A8".to_string(),
            },
            font_scale: 1.15,
            show_animations: true,
            compact_mode: false,
            dashboard_layout: vec![
                "threat-feed".to_string(),
                "alerts".to_string(),
                "metrics".to_string(),
            ],
        },
        notifications: vec![
            NotificationRule {
                channel: NotificationChannel::Email,
                frequency: Frequency::Daily,
                enabled: true,
                quiet_hours: Some((22, 7)),
            },
            NotificationRule {
                channel: NotificationChannel::Push,
                frequency: Frequency::Instant,
                enabled: true,
                quiet_hours: None,
            },
            NotificationRule {
                channel: NotificationChannel::Sms,
                frequency: Frequency::Never,
                enabled: false,
                quiet_hours: None,
            },
        ],
        privacy: PrivacyPreferences {
            profile_visibility: PrivacyLevel::Custom {
                allow_search_indexing: false,
                share_activity_status: true,
            },
            telemetry_enabled: false,
            ad_personalization: false,
            blocked_users: vec!["spam_bot_1".to_string(), "spam_bot_2".to_string()],
        },
        shortcuts,
        favorite_tags: vec![
            "rust".to_string(),
            "security".to_string(),
            "benchmarking".to_string(),
        ],
        integrations: Integrations {
            github_username: Some("randyflood".to_string()),
            calendar_connected: true,
            api_tokens,
        },
    }
}