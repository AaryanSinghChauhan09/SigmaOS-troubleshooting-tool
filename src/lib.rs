//! SigmaOS-troubleshooting-tool: System diagnostic and troubleshooting tool.
//!
//! Collect system reports, diagnose common issues, and guide users through
//! fixes. Inspired by mintreport.


/// Initialise the troubleshooting subsystem.
///
/// Call once at application startup to register diagnostic checks.
pub fn init() {
    // TODO: register built-in diagnostic checks and report collectors
}

pub mod backup;
pub mod system;
