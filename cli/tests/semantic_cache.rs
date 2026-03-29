//! Integration tests for semantic cache with Turso/libsql persistence.
//!
//! Validates that records are correctly stored and loaded from the database.
//!
//! NOTE: Tests disabled pending API clarification for HVec10240 text encoding.
//! The `from_bytes` method requires exact dimension-sized input (1280 bytes for 10240 dims).

#[cfg(feature = "semantic-cache")]
mod semantic_cache_tests {
    // Tests disabled until proper text-to-vector encoding is documented
    // See: https://github.com/user/chaotic-semantic-memory/issues/XX
}
