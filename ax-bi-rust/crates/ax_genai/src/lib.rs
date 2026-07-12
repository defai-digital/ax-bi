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

use std::cmp::Ordering;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

const NAME_MATCH_SCORE: f64 = 1.0;
const DESCRIPTION_MATCH_SCORE: f64 = 0.5;
const CERTIFIED_BONUS: f64 = 0.2;

#[derive(Debug)]
struct AssetCandidate {
    index: usize,
    asset_type: String,
    id: i64,
    uuid: String,
    name: String,
    description: String,
    certified: bool,
    owners: Vec<String>,
    tags: Vec<String>,
    relevance_score: f64,
    relevance_reason: String,
}

fn optional_string(dict: &Bound<'_, PyDict>, key: &str) -> PyResult<String> {
    Ok(dict
        .get_item(key)?
        .and_then(|value| value.extract::<String>().ok())
        .unwrap_or_default())
}

fn optional_bool(dict: &Bound<'_, PyDict>, key: &str) -> PyResult<bool> {
    Ok(dict
        .get_item(key)?
        .and_then(|value| value.extract::<bool>().ok())
        .unwrap_or(false))
}

fn optional_string_list(dict: &Bound<'_, PyDict>, key: &str) -> PyResult<Vec<String>> {
    Ok(dict
        .get_item(key)?
        .and_then(|value| value.extract::<Vec<String>>().ok())
        .unwrap_or_default())
}

fn required_id(dict: &Bound<'_, PyDict>) -> PyResult<i64> {
    dict.get_item("id")?
        .and_then(|value| value.extract::<i64>().ok())
        .ok_or_else(|| pyo3::exceptions::PyValueError::new_err("asset id must be an integer"))
}

fn score_asset(name: &str, description: &str, certified: bool, query: &str) -> f64 {
    let query_lower = query.to_lowercase();
    let name_lower = name.to_lowercase();
    let description_lower = description.to_lowercase();

    let mut score = 0.0;
    if name_lower.contains(&query_lower) {
        score += NAME_MATCH_SCORE;
    }
    if description_lower.contains(&query_lower) {
        score += DESCRIPTION_MATCH_SCORE;
    }
    if certified {
        score += CERTIFIED_BONUS;
    }

    (score * 10_000.0).round() / 10_000.0
}

fn build_reason(name: &str, description: &str, query: &str) -> String {
    let query_lower = query.to_lowercase();
    let name_lower = name.to_lowercase();
    let description_lower = description.to_lowercase();
    let mut parts = Vec::new();

    if name_lower.contains(&query_lower) {
        parts.push(format!("name matches '{}'", query));
    }
    if description_lower.contains(&query_lower) {
        parts.push(format!("description matches '{}'", query));
    }

    if parts.is_empty() {
        "tag/owner match".to_string()
    } else {
        parts.join(", ")
    }
}

/// Rank already-authorized BI assets by business-search relevance.
#[pyfunction]
pub fn rank_assets(
    py: Python<'_>,
    query: &str,
    candidates: &Bound<'_, PyAny>,
    limit: usize,
) -> PyResult<Py<PyList>> {
    let mut ranked = Vec::new();

    for (index, item) in candidates.try_iter()?.enumerate() {
        let item = item?;
        let dict = item.cast::<PyDict>()?;
        let asset_type = optional_string(dict, "asset_type")?;
        let id = required_id(dict)?;
        let uuid = optional_string(dict, "uuid")?;
        let name = optional_string(dict, "name")?;
        let description = optional_string(dict, "description")?;
        let certified = optional_bool(dict, "certified")?;
        let owners = optional_string_list(dict, "owners")?;
        let tags = optional_string_list(dict, "tags")?;

        ranked.push(AssetCandidate {
            index,
            relevance_score: score_asset(&name, &description, certified, query),
            relevance_reason: build_reason(&name, &description, query),
            asset_type,
            id,
            uuid,
            name,
            description,
            certified,
            owners,
            tags,
        });
    }

    ranked.sort_by(|left, right| {
        right
            .relevance_score
            .partial_cmp(&left.relevance_score)
            .unwrap_or(Ordering::Equal)
            .then_with(|| left.index.cmp(&right.index))
    });

    let output = PyList::empty(py);
    for asset in ranked.into_iter().take(limit) {
        let item = PyDict::new(py);
        item.set_item("asset_type", asset.asset_type)?;
        item.set_item("id", asset.id)?;
        item.set_item("uuid", asset.uuid)?;
        item.set_item("name", asset.name)?;
        item.set_item("description", asset.description)?;
        item.set_item("certified", asset.certified)?;
        item.set_item("relevance_score", asset.relevance_score)?;
        item.set_item("relevance_reason", asset.relevance_reason)?;
        item.set_item("owners", asset.owners)?;
        item.set_item("tags", asset.tags)?;
        output.append(item)?;
    }

    Ok(output.unbind())
}

#[pymodule]
fn ax_genai(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(rank_assets, module)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{build_reason, score_asset};

    #[test]
    fn scores_name_and_description_matches() {
        assert_eq!(score_asset("Sales", "Sales metrics", false, "sales"), 1.5);
    }

    #[test]
    fn adds_certified_bonus() {
        assert_eq!(score_asset("Sales", "", true, "sales"), 1.2);
    }

    #[test]
    fn builds_match_reason() {
        assert_eq!(
            build_reason("Sales", "Sales metrics", "sales"),
            "name matches 'sales', description matches 'sales'"
        );
    }

    #[test]
    fn defaults_reason_when_text_does_not_match() {
        assert_eq!(build_reason("Inventory", "", "sales"), "tag/owner match");
    }
}
