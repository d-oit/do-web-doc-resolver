//! Integration tests for semantic cache with Turso/libsql persistence.
//!
//! Validates that records are correctly stored, loaded, and removed from the database.

#[cfg(feature = "semantic-cache")]
mod semantic_cache_tests {
    use do_wdr_lib::config::Config;
    use do_wdr_lib::semantic_cache::SemanticCache;
    use do_wdr_lib::types::ResolvedResult;
    use tempfile::TempDir;

    async fn create_test_cache_in(temp_dir: &TempDir) -> SemanticCache {
        let mut config = Config::default();
        config.semantic_cache.enabled = true;
        config.semantic_cache.path = temp_dir.path().to_str().unwrap().to_string();
        config.semantic_cache.threshold = 0.85;

        SemanticCache::new(&config)
            .await
            .expect("Failed to create cache")
            .expect("Cache was disabled")
    }

    async fn create_test_cache() -> (SemanticCache, TempDir) {
        let temp_dir = tempfile::TempDir::new().expect("Failed to create temp dir");
        let cache = create_test_cache_in(&temp_dir).await;
        (cache, temp_dir)
    }

    fn create_test_result(source: &str, content: &str) -> Vec<ResolvedResult> {
        vec![ResolvedResult::new(
            "https://example.com",
            Some(content.to_string()),
            source,
            1.0,
        )]
    }

    fn create_url_result(url: &str, source: &str, content: &str) -> Vec<ResolvedResult> {
        vec![ResolvedResult::new(
            url,
            Some(content.to_string()),
            source,
            1.0,
        )]
    }

    #[tokio::test]
    async fn test_store_and_load() {
        let (cache, _temp_dir) = create_test_cache().await;

        let query = "tokio async runtime";
        let results = create_test_result("test_provider", "Test content about Tokio async runtime");
        cache
            .store(query, &results, "test_provider")
            .await
            .expect("Failed to store");

        let loaded = cache.query(query).await.expect("Failed to query");
        assert!(loaded.is_some(), "Expected cache hit for stored query");

        let loaded_results = loaded.unwrap();
        assert_eq!(loaded_results.len(), 1);
        assert_eq!(loaded_results[0].source, "test_provider");
        assert_eq!(
            loaded_results[0].content,
            Some("Test content about Tokio async runtime".to_string())
        );
    }

    #[tokio::test]
    async fn test_semantic_similarity() {
        let (cache, _temp_dir) = create_test_cache().await;

        let query = "rust programming language tutorial";
        let results = create_test_result("rust_docs", "Learn Rust programming");
        cache
            .store(query, &results, "rust_docs")
            .await
            .expect("Failed to store");

        let similar_query = "Rust programming language TUTORIAL";
        let loaded = cache.query(similar_query).await.expect("Failed to query");

        assert!(
            loaded.is_some(),
            "Expected cache hit for normalized identical query"
        );
    }

    #[tokio::test]
    async fn test_remove_entry() {
        let (cache, _temp_dir) = create_test_cache().await;

        let query = "unique test query for removal";
        let results = create_test_result("remove_test", "Content to be removed");
        cache
            .store(query, &results, "remove_test")
            .await
            .expect("Failed to store");

        let loaded = cache.query(query).await.expect("Failed to query");
        assert!(loaded.is_some(), "Expected cache hit after store");

        cache.remove(query).await.expect("Failed to remove");

        let loaded = cache.query(query).await.expect("Failed to query");
        assert!(loaded.is_none(), "Expected cache miss after remove");
    }

    #[tokio::test]
    async fn test_multiple_entries() {
        let (cache, _temp_dir) = create_test_cache().await;

        let queries = ["rust async", "python async", "go async"];
        for (i, query) in queries.iter().enumerate() {
            let results = create_test_result(
                &format!("provider_{}", i),
                &format!("Content for {}", query),
            );
            cache
                .store(query, &results, &format!("provider_{}", i))
                .await
                .expect("Failed to store");
        }

        for (i, query) in queries.iter().enumerate() {
            let loaded = cache.query(query).await.expect("Failed to query");
            assert!(loaded.is_some(), "Expected cache hit for query: {}", query);
            assert_eq!(loaded.unwrap()[0].source, format!("provider_{}", i));
        }
    }

    #[tokio::test]
    async fn test_query_url() {
        let (cache, _temp_dir) = create_test_cache().await;

        let url = "https://docs.rs/tokio";
        let results = create_test_result("jina", "Tokio documentation content");
        cache
            .store(url, &results, "jina")
            .await
            .expect("Failed to store");

        let loaded = cache.query_url(url).await.expect("Failed to query_url");
        assert!(loaded.is_some(), "Expected cache hit for URL");
        assert_eq!(loaded.unwrap().source, "jina");
    }

    #[tokio::test]
    async fn test_query_provider() {
        let (cache, _temp_dir) = create_test_cache().await;

        let query = "rust async";
        let provider = "exa_mcp";
        let key = format!("{}:{}", provider, query);
        let results = create_test_result(provider, "Exa MCP result");
        cache
            .store(&key, &results, provider)
            .await
            .expect("Failed to store");

        let loaded = cache
            .query_provider(query, provider)
            .await
            .expect("Failed to query_provider");
        assert!(
            loaded.is_some(),
            "Expected cache hit for provider-specific query"
        );
    }

    #[tokio::test]
    async fn test_url_path_order_counterexample_persistence() {
        let temp_dir = TempDir::new().expect("Failed to create temp dir");

        let url1 = "https://example.com/docs/foo/bar";
        let url2 = "https://example.com/docs/bar/foo";
        let payload1 = "Payload for FooBar";
        let payload2 = "Payload for BarFoo";

        {
            let cache = create_test_cache_in(&temp_dir).await;

            cache
                .store(url1, &create_url_result(url1, "jina", payload1), "jina")
                .await
                .expect("Failed to store url1");

            cache
                .store(url2, &create_url_result(url2, "jina", payload2), "jina")
                .await
                .expect("Failed to store url2");

            let res1 = cache.query_url(url1).await.unwrap().unwrap();
            let res2 = cache.query_url(url2).await.unwrap().unwrap();

            assert_eq!(res1.content.as_deref(), Some(payload1));
            assert_eq!(res2.content.as_deref(), Some(payload2));
        }

        // Reopen database from same directory
        {
            let cache = create_test_cache_in(&temp_dir).await;

            let res1 = cache.query_url(url1).await.unwrap().unwrap();
            let res2 = cache.query_url(url2).await.unwrap().unwrap();

            assert_eq!(res1.content.as_deref(), Some(payload1));
            assert_eq!(res2.content.as_deref(), Some(payload2));
        }
    }

    #[tokio::test]
    async fn test_case_sensitive_paths_query_values_and_fragment_policy() {
        let (cache, _temp_dir) = create_test_cache().await;

        // 1. Case-sensitive path distinction
        let url_upper = "https://example.com/docs/Foo/Bar";
        let url_lower = "https://example.com/docs/foo/bar";
        cache
            .store(
                url_upper,
                &create_url_result(url_upper, "jina", "Upper Case Path"),
                "jina",
            )
            .await
            .unwrap();
        cache
            .store(
                url_lower,
                &create_url_result(url_lower, "jina", "Lower Case Path"),
                "jina",
            )
            .await
            .unwrap();

        let res_upper = cache.query_url(url_upper).await.unwrap().unwrap();
        let res_lower = cache.query_url(url_lower).await.unwrap().unwrap();
        assert_eq!(res_upper.content.as_deref(), Some("Upper Case Path"));
        assert_eq!(res_lower.content.as_deref(), Some("Lower Case Path"));

        // 2. Query parameter values and deterministic ordering
        let url_q1 = "https://example.com/api?v=1&q=test";
        let url_q1_permuted = "https://example.com/api?q=test&v=1";
        let url_q2 = "https://example.com/api?v=2&q=test";

        cache
            .store(
                url_q1,
                &create_url_result(url_q1, "jina", "API Version 1"),
                "jina",
            )
            .await
            .unwrap();
        cache
            .store(
                url_q2,
                &create_url_result(url_q2, "jina", "API Version 2"),
                "jina",
            )
            .await
            .unwrap();

        let res_q1 = cache.query_url(url_q1).await.unwrap().unwrap();
        let res_q1_perm = cache.query_url(url_q1_permuted).await.unwrap().unwrap();
        let res_q2 = cache.query_url(url_q2).await.unwrap().unwrap();

        assert_eq!(res_q1.content.as_deref(), Some("API Version 1"));
        assert_eq!(res_q1_perm.content.as_deref(), Some("API Version 1"));
        assert_eq!(res_q2.content.as_deref(), Some("API Version 2"));

        // 3. Fragment policy (stripping fragments for base resource identity)
        let base_url = "https://example.com/page";
        cache
            .store(
                base_url,
                &create_url_result(base_url, "jina", "Base Document"),
                "jina",
            )
            .await
            .unwrap();

        let res_frag1 = cache
            .query_url("https://example.com/page#section1")
            .await
            .unwrap()
            .unwrap();
        let res_frag2 = cache
            .query_url("https://example.com/page#section2")
            .await
            .unwrap()
            .unwrap();
        assert_eq!(res_frag1.content.as_deref(), Some("Base Document"));
        assert_eq!(res_frag2.content.as_deref(), Some("Base Document"));
    }

    #[tokio::test]
    async fn test_provider_isolation_exact_and_approximate() {
        let (cache, _temp_dir) = create_test_cache().await;

        let query = "rust async web framework tutorial";
        let provider_a = "provider_a";
        let provider_b = "provider_b";

        cache
            .store(
                &format!("{}:{}", provider_a, query),
                &create_test_result(provider_a, "Content from Provider A"),
                provider_a,
            )
            .await
            .expect("Failed to store for provider A");

        // Provider B exact request must miss
        let exact_b = cache.query_provider(query, provider_b).await.unwrap();
        assert!(
            exact_b.is_none(),
            "Provider B request must not hit Provider A exact entry"
        );

        // Provider B approximate request must miss
        let approx_query = "rust async web frameworks tutorials";
        let approx_b = cache
            .query_provider(approx_query, provider_b)
            .await
            .unwrap();
        assert!(
            approx_b.is_none(),
            "Provider B approximate request must not hit Provider A candidate"
        );
    }

    #[tokio::test]
    async fn test_exact_identity_and_nl_similarity_contracts() {
        let (cache, _temp_dir) = create_test_cache().await;

        // Natural language query contract allows similarity hits
        let nl_query = "rust async web framework tutorial";
        cache
            .store(
                nl_query,
                &create_test_result("docs", "Guide to Rust"),
                "docs",
            )
            .await
            .unwrap();

        let nl_hit = cache.query("rust async web framework guide").await.unwrap();
        assert!(
            nl_hit.is_some(),
            "Natural language query should allow similarity hit"
        );

        // URL contract requires exact identity match (no approximate cross-URL hits)
        let url_a = "https://example.com/guide/part1";
        let url_b = "https://example.com/guide/part2";
        cache
            .store(
                url_a,
                &create_url_result(url_a, "jina", "Part 1 Content"),
                "jina",
            )
            .await
            .unwrap();

        let url_b_hit = cache.query_url(url_b).await.unwrap();
        assert!(
            url_b_hit.is_none(),
            "URL resolution must not return approximate candidate from another URL"
        );
    }

    #[tokio::test]
    async fn test_replacement_without_cross_scope_suppression() {
        let (cache, _temp_dir) = create_test_cache().await;

        let query = "rust concurrency patterns";
        let provider_a = "provider_a";
        let provider_b = "provider_b";

        // Store for Provider A
        cache
            .store(
                &format!("{}:{}", provider_a, query),
                &create_test_result(provider_a, "Provider A Version 1"),
                provider_a,
            )
            .await
            .unwrap();

        // Store for Provider B (must NOT be suppressed by Provider A's existing entry)
        cache
            .store(
                &format!("{}:{}", provider_b, query),
                &create_test_result(provider_b, "Provider B Version 1"),
                provider_b,
            )
            .await
            .unwrap();

        let res_a = cache
            .query_provider(query, provider_a)
            .await
            .unwrap()
            .unwrap();
        let res_b = cache
            .query_provider(query, provider_b)
            .await
            .unwrap()
            .unwrap();

        assert_eq!(res_a[0].content.as_deref(), Some("Provider A Version 1"));
        assert_eq!(res_b[0].content.as_deref(), Some("Provider B Version 1"));

        // Replace entry for Provider A (must NOT be suppressed by self or Provider B)
        cache
            .store(
                &format!("{}:{}", provider_a, query),
                &create_test_result(provider_a, "Provider A Version 2 Updated"),
                provider_a,
            )
            .await
            .unwrap();

        let res_a_updated = cache
            .query_provider(query, provider_a)
            .await
            .unwrap()
            .unwrap();
        assert_eq!(
            res_a_updated[0].content.as_deref(),
            Some("Provider A Version 2 Updated")
        );
    }

    #[tokio::test]
    async fn test_cache_stats() {
        let (cache, _temp_dir) = create_test_cache().await;

        let stats = cache.stats().await.expect("Failed to get stats");
        assert_eq!(stats.path, _temp_dir.path().to_str().unwrap());
    }
}
