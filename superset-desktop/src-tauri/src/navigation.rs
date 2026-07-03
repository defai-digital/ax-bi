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

pub fn is_internal_route(path: &str) -> bool {
    path.starts_with('/')
        && !path.starts_with("//")
        && !path.contains('\\')
        && !path.chars().any(char::is_whitespace)
}

pub fn build_navigation_script(path: &str) -> Result<String, String> {
    if !is_internal_route(path) {
        return Err("Navigation target must be an internal route".to_string());
    }

    let encoded_path = serde_json::to_string(path)
        .map_err(|error| format!("Failed to encode navigation target: {error}"))?;
    Ok(format!("window.location.assign({encoded_path});"))
}

#[cfg(test)]
mod tests {
    use super::{build_navigation_script, is_internal_route};

    #[test]
    fn internal_routes_must_stay_on_current_origin() {
        assert!(is_internal_route("/superset/welcome/"));
        assert!(is_internal_route("/explore/?slice_id=1"));
        assert!(!is_internal_route("https://example.com"));
        assert!(!is_internal_route("//example.com"));
        assert!(!is_internal_route("javascript:alert(1)"));
        assert!(!is_internal_route("/\\example.com"));
        assert!(!is_internal_route("/superset\\welcome"));
        assert!(!is_internal_route("/bad route"));
        assert!(!is_internal_route("/bad\nroute"));
    }

    #[test]
    fn navigation_script_json_encodes_route() {
        let script = build_navigation_script("/x';alert(1)//").unwrap();

        assert_eq!(script, "window.location.assign(\"/x';alert(1)//\");");
    }
}
