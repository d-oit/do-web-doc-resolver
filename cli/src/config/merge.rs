//! Per-field merge helpers.
//!
//! Each helper encodes one rule for "did the incoming layer actually set this
//! value?". Keeping them together makes the rules auditable in one read
//! instead of scattered through `Config::merge`, and keeps `mod.rs` under the
//! 500-line source limit documented in AGENTS.md.

use std::collections::HashMap;

use super::ExplicitBools;

pub(super) fn merge_value<T: PartialEq>(target: &mut T, value: T, default: T) {
    if value != default {
        *target = value;
    }
}

pub(super) fn merge_string(target: &mut String, value: String) {
    merge_value(target, value, "info".to_string());
}

/// Merge a boolean that is `true` by default.
///
/// Plain "override when true" merging makes it impossible to turn a
/// default-on feature off from a config file, because an absent key
/// deserializes to the same `true` as an explicit `enabled = true`. Presence
/// is therefore tracked in [`ExplicitBools`] at parse time and the merge only
/// applies keys the source actually specified.
pub(super) fn merge_explicit_bool(
    target: &mut bool,
    value: bool,
    key: &str,
    explicit: &ExplicitBools,
) {
    if explicit.contains(key) {
        *target = value;
    } else if value {
        *target = true;
    }
}

pub(super) fn merge_option<T>(target: &mut Option<T>, value: Option<T>) {
    if value.is_some() {
        *target = value;
    }
}

pub(super) fn merge_vec<T>(target: &mut Vec<T>, value: Vec<T>) {
    if !value.is_empty() {
        *target = value;
    }
}

pub(super) fn merge_map<K, V>(target: &mut HashMap<K, V>, value: HashMap<K, V>)
where
    K: Eq + std::hash::Hash,
{
    for (name, provider_config) in value {
        target.entry(name).or_insert(provider_config);
    }
}
