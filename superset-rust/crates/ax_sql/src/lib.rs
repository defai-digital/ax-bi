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

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ScanState {
    Default,
    SingleQuote,
    DoubleQuote,
    Backtick,
    Bracket,
    LineComment,
    BlockComment,
}

/// Collapse whitespace outside SQL strings, quoted identifiers, and comments.
#[pyfunction]
pub fn normalize_sql_whitespace(sql: &str) -> String {
    let mut output = String::with_capacity(sql.len());
    let mut chars = sql.chars().peekable();
    let mut state = ScanState::Default;
    let mut pending_space = false;

    while let Some(ch) = chars.next() {
        match state {
            ScanState::Default => {
                if ch.is_whitespace() {
                    pending_space = !output.is_empty();
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
                    }
                    '"' => {
                        output.push(ch);
                        state = ScanState::DoubleQuote;
                    }
                    '`' => {
                        output.push(ch);
                        state = ScanState::Backtick;
                    }
                    '[' => {
                        output.push(ch);
                        state = ScanState::Bracket;
                    }
                    '-' if chars.peek() == Some(&'-') => {
                        output.push(ch);
                        output.push(chars.next().expect("peeked line comment marker"));
                        state = ScanState::LineComment;
                    }
                    '/' if chars.peek() == Some(&'*') => {
                        output.push(ch);
                        output.push(chars.next().expect("peeked block comment marker"));
                        state = ScanState::BlockComment;
                    }
                    _ => output.push(ch),
                }
            }
            ScanState::SingleQuote => {
                output.push(ch);
                if ch == '\'' {
                    if chars.peek() == Some(&'\'') {
                        output.push(chars.next().expect("peeked escaped quote"));
                    } else {
                        state = ScanState::Default;
                    }
                }
            }
            ScanState::DoubleQuote => {
                output.push(ch);
                if ch == '"' {
                    if chars.peek() == Some(&'"') {
                        output.push(chars.next().expect("peeked escaped identifier quote"));
                    } else {
                        state = ScanState::Default;
                    }
                }
            }
            ScanState::Backtick => {
                output.push(ch);
                if ch == '`' {
                    if chars.peek() == Some(&'`') {
                        output.push(chars.next().expect("peeked escaped backtick"));
                    } else {
                        state = ScanState::Default;
                    }
                }
            }
            ScanState::Bracket => {
                output.push(ch);
                if ch == ']' {
                    state = ScanState::Default;
                }
            }
            ScanState::LineComment => {
                output.push(ch);
                if ch == '\n' {
                    state = ScanState::Default;
                }
            }
            ScanState::BlockComment => {
                output.push(ch);
                if ch == '*' && chars.peek() == Some(&'/') {
                    output.push(chars.next().expect("peeked block comment terminator"));
                    state = ScanState::Default;
                }
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
    use super::normalize_sql_whitespace;

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
}
