// Licensed to the Apache Software Foundation (ASF) under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  The ASF licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.

// Deep link handling for AX-BI desktop client

use log::{info, warn};
use tauri::{AppHandle, Manager, Runtime};
use url::Url;

fn parse_deep_link(url: &str) -> Option<String> {
    let parsed = Url::parse(url).ok()?;
    if parsed.scheme() != "axbi" {
        warn!("Unknown deep link scheme: {}", parsed.scheme());
        return None;
    }
    let host = parsed.host_str()?;
    let path = parsed.path().trim_start_matches('/');
    let route = match host {
        "dashboard" => {
            if path.is_empty() {
                "/dashboard/list/".to_string()
            } else {
                format!("/superset/dashboard/{}/", path)
            }
        }
        "chart" => {
            if path.is_empty() {
                "/chart/list/".to_string()
            } else {
                format!("/explore/?slice_id={}", path)
            }
        }
        "explore" => "/explore/".to_string(),
        "sqllab" | "sql" => "/sqllab/".to_string(),
        "home" => "/superset/welcome/".to_string(),
        other => {
            warn!("Unknown deep link host: {}", other);
            format!("/{}/{}", host, path)
        }
    };
    info!("Parsed deep link: {} -> {}", url, route);
    Some(route)
}

pub fn handle_deep_link<R: Runtime>(app: &AppHandle<R>, url: &str) {
    if let Some(path) = parse_deep_link(url) {
        if let Some(window) = app.get_webview_window("main") {
            let js = format!("window.location.href = '{}';", path.replace('\'', "\\'"));
            if let Err(e) = window.eval(&js) {
                warn!("Failed to navigate to deep link: {}", e);
            }
            let _ = window.show();
            let _ = window.set_focus();
        }
    }
}

pub fn setup<R: Runtime>(_app: &AppHandle<R>) -> Result<(), Box<dyn std::error::Error>> {
    info!("Deep link handler initialized");
    Ok(())
}
