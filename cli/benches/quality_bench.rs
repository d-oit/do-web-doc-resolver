use criterion::{Criterion, black_box, criterion_group, criterion_main};
use do_wdr_lib::quality::score_content;
use std::time::Duration;

fn bench_quality(c: &mut Criterion) {
    let markdown = r#"
---
relevance_score: 0.95
intent_category: Technical
token_estimate: 1500
last_updated: 2026-05-20
---

[ANCHOR: SUMMARY]
This is a high-quality document with all the required markers and some content.
It avoids noise but mentions cookies once for testing purposes.

[ANCHOR: TECHNICAL_DETAILS]
The implementation uses Rust for performance and reliability.
We ensure that the quality scoring is accurate and efficient.
Deduplication is key to high-quality synthesis.

[ANCHOR: COMPARISON]
Compared to other solutions, this one is more 2026-compliant.

[ANCHOR: CITATIONS]
[1] https://example.com/docs
[2] https://rust-lang.org

# Some more content to reach the length threshold
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
"#.repeat(10);

    let links = vec![
        "https://example.com".to_string(),
        "https://rust-lang.org".to_string(),
    ];

    let mut group = c.benchmark_group("quality");
    group.measurement_time(Duration::from_secs(5));

    group.bench_function("score_content", |b| {
        b.iter(|| {
            score_content(black_box(&markdown), black_box(&links), black_box(0.7));
        });
    });
    group.finish();
}

criterion_group!(benches, bench_quality);
criterion_main!(benches);
