#[cfg(test)]
mod tests {
    use crate::config::{Config, routing_profile_defaults};
    use crate::error::ResolverError;
    use crate::providers::QueryProvider;
    use crate::resolver::cascade::{build_budget, classify_error};
    use crate::resolver::query::QueryCascade;

    #[test]
    fn test_query_cascade_new() {
        let cascade = QueryCascade::new();
        assert!(cascade.exa_mcp.is_available());
        assert!(cascade.duckduckgo.is_available());
    }

    #[test]
    fn test_query_cascade_default() {
        let cascade = QueryCascade::default();
        assert!(cascade.exa_mcp.is_available());
    }

    #[test]
    fn test_build_budget_free() {
        let config = Config::default();
        let profile_defaults = routing_profile_defaults("free");
        let budget = build_budget(&config, &profile_defaults);
        assert_eq!(budget.max_provider_attempts, 3);
        assert_eq!(budget.max_paid_attempts, 0);
        assert!(!budget.allow_paid);
    }

    #[test]
    fn test_build_budget_balanced() {
        let config = Config::default();
        let profile_defaults = routing_profile_defaults("balanced");
        let budget = build_budget(&config, &profile_defaults);
        assert_eq!(budget.max_provider_attempts, 6);
        assert!(budget.max_paid_attempts >= 2);
        assert!(budget.allow_paid);
    }

    #[test]
    fn test_build_budget_quality() {
        let config = Config::default();
        let profile_defaults = routing_profile_defaults("quality");
        let budget = build_budget(&config, &profile_defaults);
        assert!(budget.max_provider_attempts >= 6);
        assert!(budget.allow_paid);
    }

    #[test]
    fn test_build_budget_fast() {
        let config = Config::default();
        let profile_defaults = routing_profile_defaults("fast");
        let budget = build_budget(&config, &profile_defaults);
        assert_eq!(budget.max_provider_attempts, 2);
        assert!(budget.max_paid_attempts >= 1);
        assert!(budget.allow_paid);
    }

    #[test]
    fn test_classify_error_rate_limit() {
        let err = ResolverError::RateLimit("429 rate limit".to_string());
        let classified = classify_error(&err);
        assert_eq!(classified, "rate_limited");
    }

    #[test]
    fn test_classify_error_auth() {
        let err = ResolverError::Auth("401 unauthorized".to_string());
        let classified = classify_error(&err);
        assert_eq!(classified, "auth_required");
    }

    #[test]
    fn test_classify_error_network() {
        let err = ResolverError::Network("connection refused".to_string());
        let classified = classify_error(&err);
        assert_eq!(classified, "provider_error");
    }

    #[test]
    fn test_classify_error_timeout() {
        let err = ResolverError::Network("request timeout".to_string());
        let classified = classify_error(&err);
        assert_eq!(classified, "timeout");
    }

    #[test]
    fn test_classify_error_provider_5xx() {
        let err = ResolverError::Provider("500 internal server error".to_string());
        let classified = classify_error(&err);
        assert_eq!(classified, "provider_5xx");
    }
}
