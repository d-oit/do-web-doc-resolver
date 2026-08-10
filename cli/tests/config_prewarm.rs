//! Round-trip of `[routing.prewarm]` from TOML into `PrewarmConfig`.
//!
//! The committed `config.toml` carries an explicit `[routing.prewarm]` block.
//! These tests prove the section deserializes into the typed config and that
//! the committed values match the same defaults used when the section is
//! left unset (per `cli/src/config/defaults.rs`).

use do_wdr_lib::config::Config;

#[test]
fn prewarm_config_defaults_match_committed_block() {
    let config = Config::default();
    assert!(config.routing.prewarm.enabled);
    assert_eq!(config.routing.prewarm.top_n_domains, 20);
    assert_eq!(config.routing.prewarm.max_concurrency, 4);
}

#[test]
fn prewarm_config_roundtrip_from_toml() {
    // Explicit [routing.prewarm] values deserialize into PrewarmConfig.
    let content = r#"
[routing.prewarm]
enabled = false
top_n_domains = 7
max_concurrency = 2
"#;
    let config: Config = toml::from_str(content).unwrap();
    assert!(!config.routing.prewarm.enabled);
    assert_eq!(config.routing.prewarm.top_n_domains, 7);
    assert_eq!(config.routing.prewarm.max_concurrency, 2);
}

#[test]
fn committed_config_toml_parses_with_prewarm() {
    // Guard the actual repo file, not just an inline sample: a typo (or wrong
    // type) in the committed [routing.prewarm] block must fail here, since no
    // test otherwise reads the repo-root config.toml.
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../config.toml");
    let config = Config::from_file(path).expect("committed config.toml must parse");
    assert!(config.routing.prewarm.enabled);
    assert_eq!(config.routing.prewarm.top_n_domains, 20);
    assert_eq!(config.routing.prewarm.max_concurrency, 4);
}
