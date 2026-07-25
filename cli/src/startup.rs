use crate::config::Config;
use crate::resolver::Resolver;
use anyhow::Result;
use std::sync::Arc;
use tokio::sync::Semaphore;
use tokio::task::JoinSet;

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

    let semaphore = Arc::new(Semaphore::new(max_concurrency));
    let mut join_set = JoinSet::new();

    for domain in domains {
        let url = format!("https://{}", domain);
        let resolver = resolver.clone();

        let permit = semaphore.clone().acquire_owned().await?;

        join_set.spawn(async move {
            tracing::debug!("Pre-warming domain: {}", domain);

            let result = resolver.resolve_url(&url).await;
            match result {
                Ok(_) => {
                    tracing::debug!("Pre-warm succeeded for domain: {}", domain);
                }
                Err(e) => {
                    tracing::debug!("Pre-warm failed for domain {}: {}", domain, e);
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

    tracing::info!("Cache pre-warming completed");
    Ok(())
}
