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

// Deep link handling for AX BI desktop client

use log::{info, warn};
use tauri::{AppHandle, Manager, Runtime};
use tauri_plugin_deep_link::DeepLinkExt;
use url::Url;

use crate::navigation::build_navigation_script;

fn is_dashboard_identifier(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value
            .chars()
            .all(|ch| ch.is_ascii_alphanumeric() || ch == '-' || ch == '_')
}

fn is_chart_identifier(value: &str) -> bool {
    !value.is_empty() && value.len() <= 20 && value.chars().all(|ch| ch.is_ascii_digit())
}

fn static_route(path: &str, route: &str) -> Option<String> {
    if path.is_empty() {
        Some(route.to_string())
    } else {
        warn!("Invalid static deep link path: {}", path);
        None
    }
}

fn parse_deep_link(url: &str) -> Option<String> {
    if url.contains("/../") || url.ends_with("/..") || url.contains("/./") || url.ends_with("/.") {
        warn!("Rejected deep link with dot segment: {}", url);
        return None;
    }

    let parsed = Url::parse(url).ok()?;
    if parsed.scheme() != "axbi" {
        warn!("Unknown deep link scheme: {}", parsed.scheme());
        return None;
    }
    if parsed.query().is_some() || parsed.fragment().is_some() {
        warn!("Rejected deep link with query or fragment: {}", url);
        return None;
    }
    if !parsed.username().is_empty() || parsed.password().is_some() {
        warn!("Rejected deep link with credentials: {}", url);
        return None;
    }
    let host = parsed.host_str()?;
    let path = parsed.path().trim_start_matches('/');
    let route = match host {
        "dashboard" => {
            if path.is_empty() {
                "/dashboard/list/".to_string()
            } else if is_dashboard_identifier(path) {
                format!("/ax-bi/dashboard/{path}/")
            } else {
                warn!("Invalid dashboard deep link identifier: {}", path);
                return None;
            }
        }
        "chart" => {
            if path.is_empty() {
                "/chart/list/".to_string()
            } else if is_chart_identifier(path) {
                format!("/explore/?slice_id={path}")
            } else {
                warn!("Invalid chart deep link identifier: {}", path);
                return None;
            }
        }
        "explore" => static_route(path, "/explore/")?,
        "sqllab" | "sql" => static_route(path, "/sqllab/")?,
        "home" => static_route(path, "/ax-bi/welcome/")?,
        other => {
            warn!("Unknown deep link host: {}", other);
            return None;
        }
    };
    info!("Parsed deep link: {} -> {}", url, route);
    Some(route)
}

pub fn handle_deep_link<R: Runtime>(app: &AppHandle<R>, url: &str) {
    if let Some(path) = parse_deep_link(url) {
        if let Some(window) = app.get_webview_window("main") {
            let js = match build_navigation_script(&path) {
                Ok(js) => js,
                Err(e) => {
                    warn!("Rejected deep link navigation: {}", e);
                    return;
                }
            };
            if let Err(e) = window.eval(&js) {
                warn!("Failed to navigate to deep link: {}", e);
            }
            let _ = window.show();
            let _ = window.set_focus();
        }
    }
}

pub fn setup<R: Runtime>(app: &AppHandle<R>) -> Result<(), Box<dyn std::error::Error>> {
    if let Err(error) = app.deep_link().register_all() {
        warn!("Failed to register deep link schemes: {}", error);
    }

    let app_for_events = app.clone();
    app.deep_link().on_open_url(move |event| {
        for url in event.urls() {
            handle_deep_link(&app_for_events, url.as_str());
        }
    });

    if let Some(urls) = app.deep_link().get_current()? {
        for url in urls {
            handle_deep_link(app, url.as_str());
        }
    }

    info!("Deep link handler initialized");
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::parse_deep_link;

    #[test]
    fn parses_known_deep_links() {
        assert_eq!(
            parse_deep_link("axbi://dashboard/world-banks-data"),
            Some("/ax-bi/dashboard/world-banks-data/".to_string())
        );
        assert_eq!(
            parse_deep_link("axbi://chart/42"),
            Some("/explore/?slice_id=42".to_string())
        );
        assert_eq!(
            parse_deep_link("axbi://sqllab"),
            Some("/sqllab/".to_string())
        );
    }

    #[test]
    fn rejects_unknown_or_unsafe_deep_links() {
        assert_eq!(parse_deep_link("https://dashboard/1"), None);
        assert_eq!(parse_deep_link("axbi://unknown/path"), None);
        assert_eq!(parse_deep_link("axbi://chart/1abc"), None);
        assert_eq!(parse_deep_link("axbi://chart/123456789012345678901"), None);
        assert_eq!(parse_deep_link("axbi://dashboard/../admin"), None);
        assert_eq!(parse_deep_link("axbi://dashboard/.."), None);
        assert_eq!(parse_deep_link("axbi://dashboard/1?next=/admin"), None);
        assert_eq!(parse_deep_link("axbi://chart/42#settings"), None);
        assert_eq!(parse_deep_link("axbi://user@dashboard/1"), None);
        assert_eq!(parse_deep_link("axbi://explore/extra"), None);
        assert_eq!(parse_deep_link("axbi://sqllab/query/1"), None);
        assert_eq!(parse_deep_link("axbi://home/admin"), None);
    }
}
