use crate::config::Config;
use crate::resolver::Resolver;
use anyhow::Result;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::Semaphore;
use tokio::task::JoinSet;

const PER_TASK_TIMEOUT: Duration = Duration::from_secs(30);
const OVERALL_TIMEOUT: Duration = Duration::from_secs(60);

pub async fn prewarm_cache(resolver: Arc<Resolver>, config: &Config) -> Result<()> {
    if !config.routing.prewarm.enabled {
        tracing::debug!("Cache pre-warming disabled via config");
        return Ok(());
    }

    let top_n = config.routing.prewarm.top_n_domains;
    let max_concurrency = config.routing.prewarm.max_concurrency;

    let domains = {
        let routing_memory = resolver.routing_memory();
        let memory = routing_memory.read().await;
        memory.top_domains(top_n)
    };

    if domains.is_empty() {
        tracing::debug!("No domains tracked in routing memory, skipping pre-warming");
        return Ok(());
    }

    tracing::info!(
        "Pre-warming cache for {} domains (concurrency: {})",
        domains.len(),
        max_concurrency
    );

    let resolve = move |url: String| {
        let resolver = resolver.clone();
        async move {
            resolver
                .resolve_url(&url)
                .await
                .map(|_| ())
                .map_err(anyhow::Error::from)
        }
    };

    prewarm_domains(domains, max_concurrency, resolve).await
}

/// Resolve a batch of domains with bounded concurrency, awaiting completion.
///
/// The `resolve` closure is injected so tests can exercise the semaphore and
/// timeout loop offline without a network-backed `Resolver`.
pub async fn prewarm_domains<F, Fut>(
    domains: Vec<String>,
    max_concurrency: usize,
    resolve: F,
) -> anyhow::Result<()>
where
    F: Fn(String) -> Fut + Clone + Send + 'static,
    Fut: Future<Output = anyhow::Result<()>> + Send + 'static,
{
    // A zero limit would deadlock the spawn loop on the first acquire; treat
    // it as an explicit serialization request like the CLI-side default.
    let max_concurrency = max_concurrency.max(1);

    // The overall budget covers spawning AND joining. Without this, tasks that
    // each burn PER_TASK_TIMEOUT would let the spawn phase run for many minutes
    // before the join timeout ever started counting.
    let completed = tokio::time::timeout(OVERALL_TIMEOUT, async {
        let semaphore = Arc::new(Semaphore::new(max_concurrency));
        let mut join_set = JoinSet::new();

        for domain in domains {
            let url = format!("https://{}", domain);
            let resolve = resolve.clone();

            let permit = Arc::clone(&semaphore).acquire_owned().await?;

            join_set.spawn(async move {
                tracing::debug!("Pre-warming domain: {}", domain);

                let result = tokio::time::timeout(PER_TASK_TIMEOUT, resolve(url)).await;
                match result {
                    Ok(Ok(_)) => {
                        tracing::debug!("Pre-warm succeeded for domain: {}", domain);
                    }
                    Ok(Err(e)) => {
                        tracing::warn!("Pre-warm failed for domain {}: {}", domain, e);
                    }
                    Err(_) => {
                        tracing::warn!("Pre-warm timed out for domain: {}", domain);
                    }
                }
                drop(permit);
            });
        }

        while let Some(result) = join_set.join_next().await {
            if let Err(e) = result {
                tracing::warn!("Pre-warm task panicked: {}", e);
            }
        }

        Ok::<(), anyhow::Error>(())
    })
    .await;

    match completed {
        Ok(result) => result,
        Err(_) => {
            // Dropping the timed-out future aborts all in-flight tasks.
            tracing::warn!(
                "Pre-warming timed out after {}s, abandoning remaining tasks",
                OVERALL_TIMEOUT.as_secs()
            );
            Ok(())
        }
    }?;

    tracing::info!("Cache pre-warming completed");
    Ok(())
}
