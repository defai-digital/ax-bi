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

// AX-BI Desktop Client - Main Entry Point

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod deep_link;
mod navigation;
mod tray;

use log::info;

fn main() {
    env_logger::init();
    info!("Starting AX-BI Desktop Client");

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .setup(|app| {
            info!("Application setup complete");
            let handle = app.handle().clone();
            deep_link::setup(&handle)?;
            tray::setup(&handle)?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_app_config,
            commands::navigate_to,
            commands::show_notification,
            commands::get_version,
        ])
        .run(tauri::generate_context!())
        .expect("Error while running AX-BI Desktop");
}
