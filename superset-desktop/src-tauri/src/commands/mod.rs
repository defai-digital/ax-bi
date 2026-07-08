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

// Tauri commands exposed to the frontend

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Manager, Runtime};
use url::Url;

use crate::navigation::build_navigation_script;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub server_url: String,
    pub sso_enabled: bool,
    pub version: String,
}

const DEFAULT_SERVER_URL: &str = "http://127.0.0.1:8088";
const MAX_NOTIFICATION_TITLE_CHARS: usize = 128;
const MAX_NOTIFICATION_BODY_CHARS: usize = 1024;

fn normalize_server_url(value: &str) -> Result<String, String> {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        return Err("AXBI_SERVER_URL must not be empty".to_string());
    }

    let lower_trimmed = trimmed.to_ascii_lowercase();
    if !lower_trimmed.starts_with("http://") && !lower_trimmed.starts_with("https://") {
        return Err("AXBI_SERVER_URL must be a valid HTTP(S) URL".to_string());
    }
    validate_server_url_path(raw_url_path(trimmed))?;

    let url = Url::parse(trimmed)
        .map_err(|_| "AXBI_SERVER_URL must be a valid HTTP(S) URL".to_string())?;
    if url.scheme() != "http" && url.scheme() != "https" {
        return Err("AXBI_SERVER_URL must be a valid HTTP(S) URL".to_string());
    }
    if url.host_str().is_none() {
        return Err("AXBI_SERVER_URL must include a host".to_string());
    }
    if url.query().is_some() || url.fragment().is_some() {
        return Err("AXBI_SERVER_URL must not include query or fragment".to_string());
    }
    if !url.username().is_empty() || url.password().is_some() {
        return Err("AXBI_SERVER_URL must not include credentials".to_string());
    }

    Ok(url.as_str().trim_end_matches('/').to_string())
}

fn raw_url_path(value: &str) -> &str {
    let Some(authority_start) = value.find("://") else {
        return "";
    };
    let after_authority = &value[authority_start + 3..];
    let Some(path_start) = after_authority.find('/') else {
        return "";
    };
    let path_and_after = &after_authority[path_start..];
    let path_end = path_and_after
        .find(['?', '#'])
        .unwrap_or(path_and_after.len());
    &path_and_after[..path_end]
}

fn validate_server_url_path(path: &str) -> Result<(), String> {
    for segment in path.split('/') {
        let decoded = percent_decode_path_segment(segment)?;
        if decoded == "." || decoded == ".." {
            return Err("AXBI_SERVER_URL path must not include dot segments".to_string());
        }
        if decoded.contains('/') || decoded.contains('\\') {
            return Err(
                "AXBI_SERVER_URL path must not include encoded path separators".to_string(),
            );
        }
    }

    Ok(())
}

fn percent_decode_path_segment(segment: &str) -> Result<String, String> {
    let bytes = segment.as_bytes();
    let mut decoded = Vec::with_capacity(bytes.len());
    let mut index = 0;

    while index < bytes.len() {
        if bytes[index] == b'%' {
            if index + 2 >= bytes.len() {
                return Err("AXBI_SERVER_URL path must contain valid percent-encoding".to_string());
            }
            let high = hex_value(bytes[index + 1]).ok_or_else(|| {
                "AXBI_SERVER_URL path must contain valid percent-encoding".to_string()
            })?;
            let low = hex_value(bytes[index + 2]).ok_or_else(|| {
                "AXBI_SERVER_URL path must contain valid percent-encoding".to_string()
            })?;
            decoded.push((high << 4) | low);
            index += 3;
        } else {
            decoded.push(bytes[index]);
            index += 1;
        }
    }

    String::from_utf8(decoded)
        .map_err(|_| "AXBI_SERVER_URL path must contain valid UTF-8".to_string())
}

fn hex_value(value: u8) -> Option<u8> {
    match value {
        b'0'..=b'9' => Some(value - b'0'),
        b'a'..=b'f' => Some(value - b'a' + 10),
        b'A'..=b'F' => Some(value - b'A' + 10),
        _ => None,
    }
}

fn validate_notification_input(title: &str, body: &str) -> Result<(), String> {
    if title.trim().is_empty() {
        return Err("Notification title must not be empty".to_string());
    }
    if title.chars().any(char::is_control) {
        return Err("Notification title must not contain control characters".to_string());
    }
    if body.chars().any(char::is_control) {
        return Err("Notification body must not contain control characters".to_string());
    }
    if title.chars().count() > MAX_NOTIFICATION_TITLE_CHARS {
        return Err(format!(
            "Notification title must be at most {MAX_NOTIFICATION_TITLE_CHARS} characters"
        ));
    }
    if body.chars().count() > MAX_NOTIFICATION_BODY_CHARS {
        return Err(format!(
            "Notification body must be at most {MAX_NOTIFICATION_BODY_CHARS} characters"
        ));
    }

    Ok(())
}

#[tauri::command]
pub async fn get_app_config<R: Runtime>(_app: AppHandle<R>) -> Result<AppConfig, String> {
    let server_url = std::env::var("AXBI_SERVER_URL")
        .map(|value| normalize_server_url(&value))
        .unwrap_or_else(|_| normalize_server_url(DEFAULT_SERVER_URL))?;

    Ok(AppConfig {
        server_url,
        sso_enabled: true,
        version: env!("CARGO_PKG_VERSION").to_string(),
    })
}

#[tauri::command]
pub async fn navigate_to<R: Runtime>(app: AppHandle<R>, path: String) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        let js = build_navigation_script(&path)?;
        window
            .eval(&js)
            .map_err(|e| format!("Failed to navigate: {}", e))?;
    }
    Ok(())
}

#[tauri::command]
pub async fn show_notification<R: Runtime>(
    app: AppHandle<R>,
    title: String,
    body: String,
) -> Result<(), String> {
    use tauri_plugin_notification::NotificationExt;
    validate_notification_input(&title, &body)?;
    app.notification()
        .builder()
        .title(title)
        .body(body)
        .show()
        .map_err(|e| format!("Failed to show notification: {}", e))?;
    Ok(())
}

#[tauri::command]
pub async fn get_version() -> Result<String, String> {
    Ok(env!("CARGO_PKG_VERSION").to_string())
}

#[cfg(test)]
mod tests {
    use super::{normalize_server_url, validate_notification_input, DEFAULT_SERVER_URL};

    #[test]
    fn normalizes_valid_server_urls() {
        assert_eq!(
            normalize_server_url("  https://superset.example.test/  ").unwrap(),
            "https://superset.example.test"
        );
        assert_eq!(
            normalize_server_url("https://superset.example.test/analytics/").unwrap(),
            "https://superset.example.test/analytics"
        );
        assert_eq!(
            normalize_server_url(DEFAULT_SERVER_URL).unwrap(),
            DEFAULT_SERVER_URL
        );
    }

    #[test]
    fn rejects_invalid_server_urls() {
        assert_eq!(
            normalize_server_url("   ").unwrap_err(),
            "AXBI_SERVER_URL must not be empty"
        );
        assert_eq!(
            normalize_server_url("not a url").unwrap_err(),
            "AXBI_SERVER_URL must be a valid HTTP(S) URL"
        );
        assert_eq!(
            normalize_server_url("file:///tmp/superset").unwrap_err(),
            "AXBI_SERVER_URL must be a valid HTTP(S) URL"
        );
        assert_eq!(
            normalize_server_url("http:dashboard").unwrap_err(),
            "AXBI_SERVER_URL must be a valid HTTP(S) URL"
        );
        assert_eq!(
            normalize_server_url("https:/dashboard").unwrap_err(),
            "AXBI_SERVER_URL must be a valid HTTP(S) URL"
        );
        assert_eq!(
            normalize_server_url("https://superset.example.test?tenant=ax").unwrap_err(),
            "AXBI_SERVER_URL must not include query or fragment"
        );
        assert_eq!(
            normalize_server_url("https://superset.example.test#dashboard").unwrap_err(),
            "AXBI_SERVER_URL must not include query or fragment"
        );
        assert_eq!(
            normalize_server_url("https://user:s3cr3t@superset.example.test").unwrap_err(),
            "AXBI_SERVER_URL must not include credentials"
        );
        assert_eq!(
            normalize_server_url("https://superset.example.test/../admin").unwrap_err(),
            "AXBI_SERVER_URL path must not include dot segments"
        );
        assert_eq!(
            normalize_server_url("https://superset.example.test/%2e%2e/admin").unwrap_err(),
            "AXBI_SERVER_URL path must not include dot segments"
        );
        assert_eq!(
            normalize_server_url("https://superset.example.test/superset%2fadmin").unwrap_err(),
            "AXBI_SERVER_URL path must not include encoded path separators"
        );
        assert_eq!(
            normalize_server_url("https://superset.example.test/superset%5cadmin").unwrap_err(),
            "AXBI_SERVER_URL path must not include encoded path separators"
        );
        assert_eq!(
            normalize_server_url("https://superset.example.test/superset%zz").unwrap_err(),
            "AXBI_SERVER_URL path must contain valid percent-encoding"
        );
    }

    #[test]
    fn validates_notification_input() {
        assert!(validate_notification_input("Job complete", "").is_ok());
        assert_eq!(
            validate_notification_input("   ", "body").unwrap_err(),
            "Notification title must not be empty"
        );
        assert_eq!(
            validate_notification_input("Bad\nTitle", "body").unwrap_err(),
            "Notification title must not contain control characters"
        );
        assert_eq!(
            validate_notification_input("Title", "Bad\u{0000}body").unwrap_err(),
            "Notification body must not contain control characters"
        );
        assert_eq!(
            validate_notification_input(&"a".repeat(129), "body").unwrap_err(),
            "Notification title must be at most 128 characters"
        );
        assert_eq!(
            validate_notification_input("Title", &"b".repeat(1025)).unwrap_err(),
            "Notification body must be at most 1024 characters"
        );
    }
}
