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

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub server_url: String,
    pub sso_enabled: bool,
    pub version: String,
}

#[tauri::command]
pub async fn get_app_config<R: Runtime>(_app: AppHandle<R>) -> Result<AppConfig, String> {
    Ok(AppConfig {
        server_url: std::env::var("AXBI_SERVER_URL")
            .unwrap_or_else(|_| "https://your-axbi-instance.com".to_string()),
        sso_enabled: true,
        version: env!("CARGO_PKG_VERSION").to_string(),
    })
}

#[tauri::command]
pub async fn navigate_to<R: Runtime>(app: AppHandle<R>, path: String) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        let js = format!(
            "window.location.href = '{}';",
            path.replace('\'', "\\'")
        );
        window.eval(&js).map_err(|e| format!("Failed to navigate: {}", e))?;
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
