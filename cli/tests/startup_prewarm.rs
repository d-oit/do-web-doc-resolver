//! Guards of the cache pre-warming core — offline, no network.
//!
//! `prewarm_domains` is the injected-resolve core behind `prewarm_cache`
//! (`cli/src/startup.rs`). These tests pin the "empty domains → graceful
//! skip" guard and the "every provided domain is resolved once" contract.

use do_wdr_lib::config::Config;
use do_wdr_lib::resolver::Resolver;
use do_wdr_lib::startup::{prewarm_cache, prewarm_domains};
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Duration;

#[tokio::test]
async fn prewarm_empty_domains_skips_resolve() {
    let counter = Arc::new(AtomicUsize::new(0));
    let counter_c = counter.clone();
    let resolve = move |_url: String| {
        counter_c.fetch_add(1, Ordering::SeqCst);
        async move { Ok(()) }
    };

    // No tracked domains (mirrors prewarm_cache's `domains.is_empty()` guard):
    // the resolve fn must never be called and the call must succeed gracefully.
    let result = prewarm_domains(Vec::new(), 4, resolve).await;

    assert!(result.is_ok());
    assert_eq!(counter.load(Ordering::SeqCst), 0);
}

#[tokio::test]
async fn prewarm_cache_disabled_returns_without_work() {
    // Covers the one guard the core tests cannot reach: prewarm_cache with
    // enabled=false must short-circuit before touching the resolver. The
    // explicit budget turns a regression (e.g. the guard dropping) into a
    // failure instead of a hang.
    let mut config = Config::default();
    config.routing.prewarm.enabled = false;
    config.semantic_cache.enabled = false;
    let resolver = Arc::new(Resolver::with_config(config.clone()).await);

    tokio::time::timeout(Duration::from_secs(10), prewarm_cache(resolver, &config))
        .await
        .expect("enabled=false prewarm must return promptly")
        .expect("enabled=false prewarm must succeed");
}

#[tokio::test]
async fn prewarm_invokes_resolve_for_each_domain() {
    let counter = Arc::new(AtomicUsize::new(0));
    let counter_c = counter.clone();
    let resolve = move |_url: String| {
        counter_c.fetch_add(1, Ordering::SeqCst);
        async move { Ok(()) }
    };

    let domains = vec!["a.example".to_string(), "b.example".to_string()];
    let result = prewarm_domains(domains, 2, resolve).await;

    assert!(result.is_ok());
    assert_eq!(counter.load(Ordering::SeqCst), 2);
}
