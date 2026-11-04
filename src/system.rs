//! System administration and maintenance
//! Follows: Least Privilege, Separation of Concerns, Fail-Fast

use std::collections::HashMap;

/// System resource
#[derive(Debug, Clone)]
pub struct SystemResource {
    pub name: String,
    pub usage: f32,
    pub status: ResourceStatus,
}

#[derive(Debug, Clone, PartialEq)]
pub enum ResourceStatus {
    Normal,
    Warning,
    Critical,
}

/// System monitor
pub struct SystemMonitor {
    resources: HashMap<String, SystemResource>,
}

impl SystemMonitor {
    pub fn new() -> Self {
        SystemMonitor {
            resources: HashMap::new(),
        }
    }

    pub fn add_resource(&mut self, resource: SystemResource) {
        let name = resource.name.clone();
        self.resources.insert(name, resource);
    }

    pub fn get_resource(&self, name: &str) -> Option<&SystemResource> {
        self.resources.get(name)
    }

    pub fn check_health(&self) -> bool {
        self.resources.values()
            .all(|r| r.status != ResourceStatus::Critical)
    }
}

impl Default for SystemMonitor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_system_monitor() {
        let mut monitor = SystemMonitor::new();
        let resource = SystemResource {
            name: "CPU".to_string(),
            usage: 50.0,
            status: ResourceStatus::Normal,
        };
        monitor.add_resource(resource);
        assert!(monitor.check_health());
    }
}
