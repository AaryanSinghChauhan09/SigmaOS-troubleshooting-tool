mod config;
mod error;
mod service;
mod backup;
mod system;

use config::Config;
use service::Service;
use backup::{BackupManager, SnapshotType};
use system::{SystemMonitor, SystemResource, ResourceStatus};
use std::path::PathBuf;
use anyhow::Result;

fn main() -> Result<()> {
    env_logger::init();
    
    let config = Config::default();
    let mut service = Service::new(config);
    
    service.start()?;
    println!("Service started successfully");
    
    // Demonstrate backup management
    let mut bm = BackupManager::new(10);
    let id = bm.create_snapshot(PathBuf::from("/backup"), SnapshotType::Manual)?;
    println!("Snapshot created: {}", id);
    
    // Demonstrate system monitoring
    let mut monitor = SystemMonitor::new();
    let resource = SystemResource {
        name: "CPU".to_string(),
        usage: 50.0,
        status: ResourceStatus::Normal,
    };
    monitor.add_resource(resource);
    println!("System health: {}", monitor.check_health());
    
    service.stop()?;
    println!("Service stopped successfully");
    
    Ok(())
}
