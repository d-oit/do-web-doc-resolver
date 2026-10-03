use super::*;

#[test]
fn test_default_config() {
    let config = Config::default();
    assert_eq!(config.max_chars, 8000);
    assert_eq!(config.min_chars, 200);
    assert_eq!(config.exa_results, 5);
    assert_eq!(config.tavily_results, 3);
    assert_eq!(config.output_limit, 10);
}

#[test]
fn test_api_key_lookup() {
    let config = Config::default();
    assert!(config.api_key("unknown").is_none());
}

#[test]
fn test_skip_providers() {
    let config = Config {
        skip_providers: vec!["exa".to_string(), "tavily".to_string()],
        ..Default::default()
    };

    assert!(config.is_skipped("exa"));
    assert!(config.is_skipped("tavily"));
    assert!(!config.is_skipped("firecrawl"));
}

#[test]
fn test_get_ttl() {
    let config = Config::default();
    assert_eq!(config.get_ttl("firecrawl"), 21600);
    assert_eq!(config.get_ttl("exa"), 14400);
    assert_eq!(config.get_ttl("exa_mcp"), 14400);
    assert_eq!(config.get_ttl("tavily"), 14400);
    assert_eq!(config.get_ttl("serper"), 7200);
    assert_eq!(config.get_ttl("jina"), 7200);
    assert_eq!(config.get_ttl("mistral"), 28800);
    assert_eq!(config.get_ttl("mistral_browser"), 28800);
    assert_eq!(config.get_ttl("mistral_websearch"), 28800);
    assert_eq!(config.get_ttl("duckduckgo"), 3600);
    assert_eq!(config.get_ttl("llms_txt"), 28800);
    assert_eq!(config.get_ttl("synthesis"), 43200);
    assert_eq!(config.get_ttl("unknown"), 3600);
}

/// Regression test: `enabled = false` in a config file must survive the
/// merge. Previously `merge_bool` only applied `true`, so every
/// default-on feature could be turned off by env var or CLI flag but never
/// by the config file itself.
#[test]
fn test_config_file_can_disable_default_on_features() {
    let dir = std::env::temp_dir().join(format!("wdr-config-merge-{}", std::process::id()));
    std::fs::create_dir_all(&dir).expect("create temp dir");
    let path = dir.join("disable.toml");

    std::fs::write(
        &path,
        r#"
max_chars = 1234

[semantic_cache]
enabled = false

[cache.synthesis]
enabled = false

[routing.prewarm]
enabled = false
"#,
    )
    .expect("write config");

    let config = Config::from_file(&path).expect("parse config");

    assert!(
        !config.semantic_cache.enabled,
        "semantic_cache must be disabled"
    );
    assert!(
        !config.cache.synthesis.enabled,
        "synthesis cache must be disabled"
    );
    assert!(!config.routing.prewarm.enabled, "prewarm must be disabled");
    // Non-boolean fields must still merge normally.
    assert_eq!(config.max_chars, 1234);

    let _ = std::fs::remove_file(&path);
    let _ = std::fs::remove_dir(&dir);
}

/// `disable_routing_memory` is default-off, so the presence tracking only
/// has to make an explicit `true` survive the merge. Covered here because it
/// shares `EXPLICIT_BOOL_KEYS` with the default-on flags and would otherwise
/// be the one untested entry.
#[test]
fn test_explicit_true_survives_merge_for_default_off_flag() {
    let dir = std::env::temp_dir().join(format!("wdr-config-flag-{}", std::process::id()));
    std::fs::create_dir_all(&dir).expect("create temp dir");
    let path = dir.join("flag.toml");

    std::fs::write(&path, "disable_routing_memory = true\n").expect("write config");
    let on = Config::from_file(&path).expect("parse config");
    assert!(on.disable_routing_memory);

    // Absent must leave the default alone in both directions.
    std::fs::write(&path, "log_level = \"debug\"\n").expect("write config");
    let absent = Config::from_file(&path).expect("parse config");
    assert!(!absent.disable_routing_memory);

    // Explicitly false must not resurrect a true default.
    std::fs::write(&path, "disable_routing_memory = false\n").expect("write config");
    let off = Config::from_file(&path).expect("parse config");
    assert!(!off.disable_routing_memory);

    let _ = std::fs::remove_file(&path);
    let _ = std::fs::remove_dir(&dir);
}

/// A config file that omits these keys must not disable them.
#[test]
fn test_absent_bools_keep_defaults() {
    let dir = std::env::temp_dir().join(format!("wdr-config-absent-{}", std::process::id()));
    std::fs::create_dir_all(&dir).expect("create temp dir");
    let path = dir.join("minimal.toml");

    std::fs::write(&path, "log_level = \"debug\"\n").expect("write config");

    let config = Config::from_file(&path).expect("parse config");

    assert!(config.semantic_cache.enabled);
    assert!(config.cache.synthesis.enabled);
    assert!(config.routing.prewarm.enabled);
    assert_eq!(config.log_level, "debug");

    let _ = std::fs::remove_file(&path);
    let _ = std::fs::remove_dir(&dir);
}
