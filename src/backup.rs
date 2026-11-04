//! Backup and snapshot management
//! Follows: Fail-Fast, Defensive Programming, Reliability

use std::path::PathBuf;

/// Snapshot type
#[derive(Debug, Clone, PartialEq)]
pub enum SnapshotType {
    Manual,
    Scheduled,
    PreUpdate,
    PreInstall,
}

/// Snapshot metadata
#[derive(Debug, Clone)]
pub struct Snapshot {
    pub id: String,
    pub timestamp: u64,
    pub snapshot_type: SnapshotType,
    pub size: u64,
    pub path: PathBuf,
}

impl Snapshot {
    pub fn new(id: String, snapshot_type: SnapshotType, path: PathBuf) -> Self {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();
        
        Snapshot {
            id,
            timestamp: now,
            snapshot_type,
            size: 0,
            path,
        }
    }
}

/// Backup manager
pub struct BackupManager {
    snapshots: Vec<Snapshot>,
    max_snapshots: usize,
}

impl BackupManager {
    pub fn new(max_snapshots: usize) -> Self {
        BackupManager {
            snapshots: Vec::new(),
            max_snapshots,
        }
    }

    pub fn create_snapshot(&mut self, path: PathBuf, snapshot_type: SnapshotType) -> Result<String, &'static str> {
        let id = format!("snapshot_{}", self.snapshots.len() + 1);
        let snapshot = Snapshot::new(id.clone(), snapshot_type, path);
        
        self.snapshots.push(snapshot);
        
        // Enforce max snapshots
        if self.snapshots.len() > self.max_snapshots {
            self.snapshots.remove(0);
        }
        
        Ok(id)
    }

    pub fn list_snapshots(&self) -> Vec<&Snapshot> {
        self.snapshots.iter().collect()
    }

    pub fn restore_snapshot(&self, id: &str) -> Result<(), &'static str> {
        self.snapshots.iter()
            .find(|s| s.id == id)
            .ok_or("Snapshot not found")?;
        Ok(())
    }
}

impl Default for BackupManager {
    fn default() -> Self {
        Self::new(10)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_backup_manager() {
        let mut bm = BackupManager::new(5);
        let id = bm.create_snapshot(PathBuf::from("/test"), SnapshotType::Manual).unwrap();
        assert!(!id.is_empty());
    }
}
