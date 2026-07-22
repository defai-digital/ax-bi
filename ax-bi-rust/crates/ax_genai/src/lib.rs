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
const TAG_MATCH_SCORE: f64 = 0.3;
const OWNER_MATCH_SCORE: f64 = 0.1;
/// Hard cap so pathological candidate lists cannot balloon memory.
const MAX_CANDIDATES: usize = 50_000;

#[derive(Debug, Clone)]
struct AssetInput {
    index: usize,
    asset_type: String,
    id: i64,
    uuid: String,
    name: String,
    description: String,
    certified: bool,
    owners: Vec<String>,
    tags: Vec<String>,
    /// Incoming score from Python (lexical and/or semantic/embedding).
    input_relevance_score: f64,
}

#[derive(Debug, Clone)]
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

fn field_type_error(key: &str, expected: &str) -> PyErr {
    pyo3::exceptions::PyValueError::new_err(format!(
        "asset field '{key}' must be {expected}"
    ))
}

fn optional_string(dict: &Bound<'_, PyDict>, key: &str) -> PyResult<String> {
    match dict.get_item(key)? {
        None => Ok(String::new()),
        Some(value) if value.is_none() => Ok(String::new()),
        Some(value) => value
            .extract::<String>()
            .map_err(|_| field_type_error(key, "a string or null")),
    }
}

fn optional_bool(dict: &Bound<'_, PyDict>, key: &str) -> PyResult<bool> {
    match dict.get_item(key)? {
        None => Ok(false),
        Some(value) if value.is_none() => Ok(false),
        Some(value) => value
            .extract::<bool>()
            .map_err(|_| field_type_error(key, "a boolean or null")),
    }
}

fn optional_string_list(dict: &Bound<'_, PyDict>, key: &str) -> PyResult<Vec<String>> {
    match dict.get_item(key)? {
        None => Ok(Vec::new()),
        Some(value) if value.is_none() => Ok(Vec::new()),
        Some(value) => value
            .extract::<Vec<String>>()
            .map_err(|_| field_type_error(key, "a list of strings or null")),
    }
}

fn optional_f64(dict: &Bound<'_, PyDict>, key: &str) -> PyResult<f64> {
    match dict.get_item(key)? {
        None => Ok(0.0),
        Some(value) if value.is_none() => Ok(0.0),
        Some(value) => value
            .extract::<f64>()
            .map_err(|_| field_type_error(key, "a number or null")),
    }
}

fn required_id(dict: &Bound<'_, PyDict>) -> PyResult<i64> {
    match dict.get_item("id")? {
        None => Err(pyo3::exceptions::PyValueError::new_err(
            "asset id must be an integer",
        )),
        Some(value) if value.is_none() => Err(pyo3::exceptions::PyValueError::new_err(
            "asset id must be an integer",
        )),
        Some(value) => value.extract::<i64>().map_err(|_| {
            pyo3::exceptions::PyValueError::new_err("asset id must be an integer")
        }),
    }
}

fn round_score(score: f64) -> f64 {
    (score * 10_000.0).round() / 10_000.0
}

fn list_contains_query(items: &[String], query_lower: &str) -> bool {
    if query_lower.is_empty() {
        return false;
    }
    items
        .iter()
        .any(|item| item.to_lowercase().contains(query_lower))
}

/// Lexical match score (name/description/certified/tags/owners) without the
/// incoming Python relevance_score.
fn lexical_score(
    name: &str,
    description: &str,
    certified: bool,
    owners: &[String],
    tags: &[String],
    query_lower: &str,
) -> f64 {
    if query_lower.is_empty() {
        return if certified {
            round_score(CERTIFIED_BONUS)
        } else {
            0.0
        };
    }

    let name_lower = name.to_lowercase();
    let description_lower = description.to_lowercase();

    let mut score = 0.0;
    if name_lower.contains(query_lower) {
        score += NAME_MATCH_SCORE;
    }
    if description_lower.contains(query_lower) {
        score += DESCRIPTION_MATCH_SCORE;
    }
    if certified {
        score += CERTIFIED_BONUS;
    }
    if list_contains_query(tags, query_lower) {
        score += TAG_MATCH_SCORE;
    }
    if list_contains_query(owners, query_lower) {
        score += OWNER_MATCH_SCORE;
    }

    round_score(score)
}

/// Blend incoming (semantic/embedding/prior) score with lexical signals so
/// Python-provided relevance is never discarded.
fn score_asset(
    name: &str,
    description: &str,
    certified: bool,
    owners: &[String],
    tags: &[String],
    query_lower: &str,
    input_relevance_score: f64,
) -> f64 {
    round_score(
        input_relevance_score
            + lexical_score(name, description, certified, owners, tags, query_lower),
    )
}

fn build_reason(
    name: &str,
    description: &str,
    owners: &[String],
    tags: &[String],
    query: &str,
    query_lower: &str,
    input_relevance_score: f64,
) -> String {
    let name_lower = name.to_lowercase();
    let description_lower = description.to_lowercase();
    let mut parts = Vec::new();

    if !query_lower.is_empty() {
        if name_lower.contains(query_lower) {
            parts.push(format!("name matches '{query}'"));
        }
        if description_lower.contains(query_lower) {
            parts.push(format!("description matches '{query}'"));
        }
        if list_contains_query(tags, query_lower) {
            parts.push("tag match".to_string());
        }
        if list_contains_query(owners, query_lower) {
            parts.push("owner match".to_string());
        }
    }

    if parts.is_empty() {
        if input_relevance_score > 0.0 {
            "prior relevance".to_string()
        } else {
            "low text match".to_string()
        }
    } else {
        parts.join(", ")
    }
}

fn compare_candidates(left: &AssetCandidate, right: &AssetCandidate) -> Ordering {
    right
        .relevance_score
        .partial_cmp(&left.relevance_score)
        .unwrap_or(Ordering::Equal)
        .then_with(|| left.index.cmp(&right.index))
}

/// Rank already-authorized BI assets by business-search relevance.
#[pyfunction]
pub fn rank_assets(
    py: Python<'_>,
    query: &str,
    candidates: &Bound<'_, PyAny>,
    limit: usize,
) -> PyResult<Py<PyList>> {
    let mut inputs = Vec::new();

    for (index, item) in candidates.try_iter()?.enumerate() {
        if index >= MAX_CANDIDATES {
            break;
        }
        let item = item?;
        let dict = item.cast::<PyDict>()?;
        inputs.push(AssetInput {
            index,
            asset_type: optional_string(dict, "asset_type")?,
            id: required_id(dict)?,
            uuid: optional_string(dict, "uuid")?,
            name: optional_string(dict, "name")?,
            description: optional_string(dict, "description")?,
            certified: optional_bool(dict, "certified")?,
            owners: optional_string_list(dict, "owners")?,
            tags: optional_string_list(dict, "tags")?,
            input_relevance_score: optional_f64(dict, "relevance_score")?,
        });
    }

    let query_owned = query.to_owned();
    // Release the GIL while scoring/sorting pure Rust data.
    let ranked = py.detach(|| {
        let query_lower = query_owned.to_lowercase();
        let mut ranked: Vec<AssetCandidate> = inputs
            .into_iter()
            .map(|input| {
                let relevance_score = score_asset(
                    &input.name,
                    &input.description,
                    input.certified,
                    &input.owners,
                    &input.tags,
                    &query_lower,
                    input.input_relevance_score,
                );
                let relevance_reason = build_reason(
                    &input.name,
                    &input.description,
                    &input.owners,
                    &input.tags,
                    &query_owned,
                    &query_lower,
                    input.input_relevance_score,
                );
                AssetCandidate {
                    index: input.index,
                    asset_type: input.asset_type,
                    id: input.id,
                    uuid: input.uuid,
                    name: input.name,
                    description: input.description,
                    certified: input.certified,
                    owners: input.owners,
                    tags: input.tags,
                    relevance_score,
                    relevance_reason,
                }
            })
            .collect();

        // Bounded top-k selection: partial select then sort only the head.
        if limit == 0 {
            ranked.clear();
        } else if ranked.len() > limit {
            ranked.select_nth_unstable_by(limit, compare_candidates);
            ranked.truncate(limit);
            ranked.sort_by(compare_candidates);
        } else {
            ranked.sort_by(compare_candidates);
        }

        ranked
    });

    let output = PyList::empty(py);
    for asset in ranked {
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
    use super::{
        build_reason, lexical_score, score_asset, AssetCandidate, CERTIFIED_BONUS,
        DESCRIPTION_MATCH_SCORE, NAME_MATCH_SCORE, OWNER_MATCH_SCORE, TAG_MATCH_SCORE,
    };

    #[test]
    fn scores_name_and_description_matches() {
        assert_eq!(
            lexical_score("Sales", "Sales metrics", false, &[], &[], "sales"),
            1.5
        );
    }

    #[test]
    fn adds_certified_bonus() {
        assert_eq!(
            lexical_score("Sales", "", true, &[], &[], "sales"),
            1.2
        );
    }

    #[test]
    fn scores_tag_and_owner_matches() {
        let tags = vec!["sales".to_string()];
        let owners = vec!["alice".to_string()];
        assert_eq!(
            lexical_score("Inventory", "", false, &owners, &tags, "sales"),
            TAG_MATCH_SCORE
        );
        assert_eq!(
            lexical_score("Inventory", "", false, &owners, &[], "alice"),
            OWNER_MATCH_SCORE
        );
    }

    #[test]
    fn blends_incoming_relevance_score() {
        let blended = score_asset(
            "Other",
            "",
            false,
            &[],
            &[],
            "sales",
            0.85, // semantic/embedding score from Python
        );
        // No lexical match: pass-through of input only.
        assert_eq!(blended, 0.85);

        let with_name = score_asset("Sales", "", false, &[], &[], "sales", 0.85);
        assert_eq!(with_name, 0.85 + NAME_MATCH_SCORE);

        let with_all = score_asset(
            "Sales",
            "Sales metrics",
            true,
            &[],
            &[],
            "sales",
            0.5,
        );
        assert_eq!(
            with_all,
            0.5 + NAME_MATCH_SCORE + DESCRIPTION_MATCH_SCORE + CERTIFIED_BONUS
        );
    }

    #[test]
    fn relevance_score_blend_influences_ranking_order() {
        // Two assets with equal lexical signal; higher input score should win.
        let low_prior = score_asset("Sales A", "", false, &[], &[], "sales", 0.1);
        let high_prior = score_asset("Sales B", "", false, &[], &[], "sales", 0.9);
        assert!(high_prior > low_prior);

        // Semantic-only asset (no text match) can outrank weak lexical when prior is high.
        let semantic_only = score_asset("Inventory", "", false, &[], &[], "sales", 2.0);
        let weak_lexical = score_asset("Sales", "", false, &[], &[], "sales", 0.0);
        assert!(semantic_only > weak_lexical);
    }

    #[test]
    fn builds_match_reason() {
        assert_eq!(
            build_reason(
                "Sales",
                "Sales metrics",
                &[],
                &[],
                "sales",
                "sales",
                0.0
            ),
            "name matches 'sales', description matches 'sales'"
        );
    }

    #[test]
    fn builds_tag_owner_reason_when_matched() {
        let tags = vec!["finance".to_string()];
        let owners = vec!["bob".to_string()];
        assert_eq!(
            build_reason("Inventory", "", &owners, &tags, "finance", "finance", 0.0),
            "tag match"
        );
        assert_eq!(
            build_reason("Inventory", "", &owners, &tags, "bob", "bob", 0.0),
            "owner match"
        );
    }

    #[test]
    fn truthful_reason_when_nothing_matched() {
        assert_eq!(
            build_reason("Inventory", "", &[], &[], "sales", "sales", 0.0),
            "low text match"
        );
        assert_eq!(
            build_reason("Inventory", "", &[], &[], "sales", "sales", 0.42),
            "prior relevance"
        );
    }

    #[test]
    fn compare_candidates_orders_by_score_then_index() {
        let a = AssetCandidate {
            index: 1,
            asset_type: String::new(),
            id: 1,
            uuid: String::new(),
            name: String::new(),
            description: String::new(),
            certified: false,
            owners: vec![],
            tags: vec![],
            relevance_score: 1.0,
            relevance_reason: String::new(),
        };
        let b = AssetCandidate {
            index: 0,
            relevance_score: 2.0,
            ..a.clone()
        };
        let c = AssetCandidate {
            index: 2,
            relevance_score: 1.0,
            ..a.clone()
        };
        // Higher score first.
        assert_eq!(super::compare_candidates(&b, &a), std::cmp::Ordering::Less);
        // Equal score: lower index first.
        assert_eq!(super::compare_candidates(&a, &c), std::cmp::Ordering::Less);
    }
}
