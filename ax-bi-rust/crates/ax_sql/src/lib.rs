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

use pyo3::prelude::*;

#[derive(Clone, Debug, Eq, PartialEq)]
enum ScanState {
    Default,
    SingleQuote,
    DoubleQuote,
    Backtick,
    Bracket,
    LineComment,
    BlockComment { depth: usize },
    /// PostgreSQL dollar-quoted string body; tag is between the `$` markers.
    DollarQuote { tag: String },
}

/// Match Python `str.isspace()` for the characters we care about.
///
/// Rust's [`char::is_whitespace`] follows Unicode White_Space and does **not**
/// treat ASCII file/group/record/unit separators (`\x1c`–`\x1f`) as whitespace,
/// while Python does. Align with Python so kernels stay parity-compatible.
#[inline]
fn is_sql_whitespace(ch: char) -> bool {
    ch.is_whitespace() || matches!(ch, '\u{001C}'..='\u{001F}')
}

#[inline]
fn is_dollar_tag_char(ch: char) -> bool {
    ch.is_ascii_alphanumeric() || ch == '_'
}

/// Try to parse a PostgreSQL dollar-quote opener starting at `chars[index] == '$'`.
/// Returns `(tag, index_after_opener)` when `$tag$` is present.
fn parse_dollar_quote_opener(chars: &[char], index: usize) -> Option<(String, usize)> {
    if index >= chars.len() || chars[index] != '$' {
        return None;
    }
    let mut cursor = index + 1;
    while cursor < chars.len() && is_dollar_tag_char(chars[cursor]) {
        cursor += 1;
    }
    if cursor < chars.len() && chars[cursor] == '$' {
        let tag: String = chars[index + 1..cursor].iter().collect();
        Some((tag, cursor + 1))
    } else {
        None
    }
}

/// Collapse whitespace outside SQL strings, quoted identifiers, and comments.
#[pyfunction]
pub fn normalize_sql_whitespace(sql: &str) -> String {
    let chars: Vec<char> = sql.chars().collect();
    let mut output = String::with_capacity(sql.len());
    let mut index = 0;
    let mut state = ScanState::Default;
    let mut pending_space = false;

    while index < chars.len() {
        let ch = chars[index];
        let next = chars.get(index + 1).copied();

        match &state {
            ScanState::Default => {
                if is_sql_whitespace(ch) {
                    pending_space = !output.is_empty();
                    index += 1;
                    continue;
                }

                if pending_space && !output.ends_with(' ') {
                    output.push(' ');
                }
                pending_space = false;

                match ch {
                    '\'' => {
                        output.push(ch);
                        state = ScanState::SingleQuote;
                        index += 1;
                    }
                    '"' => {
                        output.push(ch);
                        state = ScanState::DoubleQuote;
                        index += 1;
                    }
                    '`' => {
                        output.push(ch);
                        state = ScanState::Backtick;
                        index += 1;
                    }
                    '[' => {
                        output.push(ch);
                        state = ScanState::Bracket;
                        index += 1;
                    }
                    '-' if next == Some('-') => {
                        output.push(ch);
                        output.push('-');
                        state = ScanState::LineComment;
                        index += 2;
                    }
                    '/' if next == Some('*') => {
                        output.push(ch);
                        output.push('*');
                        state = ScanState::BlockComment { depth: 1 };
                        index += 2;
                    }
                    '$' => {
                        if let Some((tag, after)) = parse_dollar_quote_opener(&chars, index) {
                            for c in &chars[index..after] {
                                output.push(*c);
                            }
                            state = ScanState::DollarQuote { tag };
                            index = after;
                        } else {
                            output.push(ch);
                            index += 1;
                        }
                    }
                    _ => {
                        output.push(ch);
                        index += 1;
                    }
                }
            }
            ScanState::SingleQuote => {
                // Backslash escapes (MySQL / PostgreSQL E'...') — keep next char
                // literal so `\'` does not terminate the string.
                if ch == '\\' && next.is_some() {
                    output.push(ch);
                    output.push(next.unwrap());
                    index += 2;
                } else if ch == '\'' {
                    output.push(ch);
                    if next == Some('\'') {
                        output.push('\'');
                        index += 2;
                    } else {
                        state = ScanState::Default;
                        index += 1;
                    }
                } else {
                    output.push(ch);
                    index += 1;
                }
            }
            ScanState::DoubleQuote => {
                if ch == '\\' && next.is_some() {
                    output.push(ch);
                    output.push(next.unwrap());
                    index += 2;
                } else if ch == '"' {
                    output.push(ch);
                    if next == Some('"') {
                        output.push('"');
                        index += 2;
                    } else {
                        state = ScanState::Default;
                        index += 1;
                    }
                } else {
                    output.push(ch);
                    index += 1;
                }
            }
            ScanState::Backtick => {
                output.push(ch);
                if ch == '`' {
                    if next == Some('`') {
                        output.push('`');
                        index += 2;
                    } else {
                        state = ScanState::Default;
                        index += 1;
                    }
                } else {
                    index += 1;
                }
            }
            ScanState::Bracket => {
                // T-SQL: `]]` is an escaped `]` inside `[...]` identifiers.
                output.push(ch);
                if ch == ']' {
                    if next == Some(']') {
                        output.push(']');
                        index += 2;
                    } else {
                        state = ScanState::Default;
                        index += 1;
                    }
                } else {
                    index += 1;
                }
            }
            ScanState::LineComment => {
                output.push(ch);
                if ch == '\n' {
                    state = ScanState::Default;
                }
                index += 1;
            }
            ScanState::BlockComment { depth } => {
                let depth = *depth;
                if ch == '/' && next == Some('*') {
                    output.push('/');
                    output.push('*');
                    state = ScanState::BlockComment { depth: depth + 1 };
                    index += 2;
                } else if ch == '*' && next == Some('/') {
                    output.push('*');
                    output.push('/');
                    if depth <= 1 {
                        state = ScanState::Default;
                    } else {
                        state = ScanState::BlockComment { depth: depth - 1 };
                    }
                    index += 2;
                } else {
                    output.push(ch);
                    index += 1;
                }
            }
            ScanState::DollarQuote { tag } => {
                // Look for closing `$tag$` without collapsing inner whitespace.
                if ch == '$' {
                    let tag_len = tag.chars().count();
                    let end = index + 1 + tag_len + 1;
                    if end <= chars.len() {
                        let tag_slice: String = chars[index + 1..index + 1 + tag_len]
                            .iter()
                            .collect();
                        if tag_slice == *tag && chars[index + 1 + tag_len] == '$' {
                            for c in &chars[index..end] {
                                output.push(*c);
                            }
                            state = ScanState::Default;
                            index = end;
                            continue;
                        }
                    }
                }
                output.push(ch);
                index += 1;
            }
        }
    }

    if output.ends_with(' ') {
        output.pop();
    }

    output
}

#[pymodule]
fn ax_sql(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(normalize_sql_whitespace, module)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{is_sql_whitespace, normalize_sql_whitespace};

    #[test]
    fn collapses_whitespace_outside_literals() {
        assert_eq!(
            normalize_sql_whitespace(" SELECT   *\nFROM   table\nWHERE id = 1 "),
            "SELECT * FROM table WHERE id = 1"
        );
    }

    #[test]
    fn preserves_string_literal_whitespace() {
        assert_eq!(
            normalize_sql_whitespace("SELECT  'a   b',  'it''s ok'"),
            "SELECT 'a   b', 'it''s ok'"
        );
    }

    #[test]
    fn preserves_quoted_identifier_whitespace() {
        assert_eq!(
            normalize_sql_whitespace("SELECT  \"a   b\",  `c   d`, [e   f]"),
            "SELECT \"a   b\", `c   d`, [e   f]"
        );
    }

    #[test]
    fn preserves_comment_body() {
        assert_eq!(
            normalize_sql_whitespace("SELECT 1  -- keep   comment\n FROM t"),
            "SELECT 1 -- keep   comment\n FROM t"
        );
        assert_eq!(
            normalize_sql_whitespace("SELECT  /* keep   block */ 1"),
            "SELECT /* keep   block */ 1"
        );
    }

    #[test]
    fn dollar_quote_preserves_inner_whitespace() {
        assert_eq!(
            normalize_sql_whitespace("SELECT  $$a   b\nc$$  ,  $tag$ x  y $tag$"),
            "SELECT $$a   b\nc$$ , $tag$ x  y $tag$"
        );
        // Nested-looking tags must only close on exact tag match.
        assert_eq!(
            normalize_sql_whitespace("SELECT $a$ $b$ inside $b$ $a$"),
            "SELECT $a$ $b$ inside $b$ $a$"
        );
    }

    #[test]
    fn bracket_double_close_escape() {
        // T-SQL: [a]]b] is identifier a]b
        assert_eq!(
            normalize_sql_whitespace("SELECT  [a]]b]  FROM  t"),
            "SELECT [a]]b] FROM t"
        );
        assert_eq!(
            normalize_sql_whitespace("SELECT [keep  ]]  spaces] FROM t"),
            "SELECT [keep  ]]  spaces] FROM t"
        );
    }

    #[test]
    fn nested_block_comments() {
        assert_eq!(
            normalize_sql_whitespace("SELECT  /* outer /* inner */ still */  1"),
            "SELECT /* outer /* inner */ still */ 1"
        );
    }

    #[test]
    fn backslash_escapes_in_strings() {
        assert_eq!(
            normalize_sql_whitespace(r#"SELECT  'it\'s   fine'  ,  "a\"b""#),
            r#"SELECT 'it\'s   fine' , "a\"b""#
        );
    }

    #[test]
    fn whitespace_predicate_matches_python_control_chars() {
        for code in [0x1c_u32, 0x1d, 0x1e, 0x1f] {
            let ch = char::from_u32(code).unwrap();
            assert!(
                is_sql_whitespace(ch),
                "U+{code:04X} should be whitespace like Python str.isspace()"
            );
        }
        assert_eq!(
            normalize_sql_whitespace("SELECT\u{001C}1\u{001F}FROM\u{0009}t"),
            "SELECT 1 FROM t"
        );
    }
}
