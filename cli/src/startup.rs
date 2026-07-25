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
    let max_concurrency = config.routing.prewarm.max_concurrency.max(1);

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

    let semaphore = Arc::new(Semaphore::new(max_concurrency));
    let mut join_set = JoinSet::new();

    for domain in domains {
        let url = format!("https://{}", domain);
        let resolver = resolver.clone();

        let permit = Arc::clone(&semaphore).acquire_owned().await?;

        join_set.spawn(async move {
            tracing::debug!("Pre-warming domain: {}", domain);

            let result = tokio::time::timeout(PER_TASK_TIMEOUT, resolver.resolve_url(&url)).await;
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

    let deadline = tokio::time::sleep(OVERALL_TIMEOUT);
    tokio::pin!(deadline);

    loop {
        tokio::select! {
            Some(result) = join_set.join_next() => {
                if let Err(e) = result {
                    tracing::warn!("Pre-warm task panicked: {}", e);
                }
            }
            _ = &mut deadline => {
                tracing::warn!("Pre-warming timed out after {}s, abandoning remaining tasks", OVERALL_TIMEOUT.as_secs());
                join_set.abort_all();
                break;
            }
            else => break,
        }
    }

    tracing::info!("Cache pre-warming completed");
    Ok(())
}
