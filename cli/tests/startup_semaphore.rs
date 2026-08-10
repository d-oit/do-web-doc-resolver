//! Concurrency limits of the cache pre-warming core — offline, no network.
//!
//! Verifies the semaphore bounds peak in-flight work to `max_concurrency` and
//! that the acquire/join loop completes without deadlock or the overall timeout.

use do_wdr_lib::startup::prewarm_domains;
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Duration;

#[tokio::test]
async fn max_concurrency_respected() {
    let peak = Arc::new(AtomicUsize::new(0));
    let in_flight = Arc::new(AtomicUsize::new(0));
    let peak_c = peak.clone();
    let in_flight_c = in_flight.clone();
    let resolve = move |_url: String| {
        let peak = peak_c.clone();
        let in_flight = in_flight_c.clone();
        async move {
            let current = in_flight.fetch_add(1, Ordering::SeqCst) + 1;
            peak.fetch_max(current, Ordering::SeqCst);
            tokio::time::sleep(Duration::from_millis(10)).await;
            in_flight.fetch_sub(1, Ordering::SeqCst);
            Ok(())
        }
    };

    let domains: Vec<String> = (0..6).map(|i| format!("{}.example", i)).collect();
    let result = prewarm_domains(domains, 2, resolve).await;

    assert!(result.is_ok());
    let observed_peak = peak.load(Ordering::SeqCst);
    assert!(
        observed_peak <= 2,
        "peak concurrency {observed_peak} exceeded limit 2"
    );
    assert_eq!(
        in_flight.load(Ordering::SeqCst),
        0,
        "all tasks must complete and release their permit"
    );
}

#[tokio::test]
async fn prewarm_without_deadlock_or_timeout() {
    let resolve = move |_url: String| async move {
        tokio::time::sleep(Duration::from_millis(1)).await;
        Ok(())
    };

    // 20 domains, 4-permit semaphore: the acquire loop must drain the queue and
    // join every task. A deadlocked acquire would hang past the test's timeout.
    let domains: Vec<String> = (0..20).map(|i| format!("{}.example", i)).collect();
    let result = prewarm_domains(domains, 4, resolve).await;

    assert!(result.is_ok());
}
