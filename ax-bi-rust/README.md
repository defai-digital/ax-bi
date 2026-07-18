<!--
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
-->

# AX BI Rust Kernels

This workspace contains optional Rust kernels for AX BI runtime modernization.
The `ax_sql` crate exposes a narrow PyO3 helper for SQL whitespace
normalization. The `ax_genai` crate exposes GenAI helper kernels such as asset
search ranking. AX BI imports these only when built and enabled; Python
fallback behavior remains available.

**Rust**: 1.85 or later (`rust-version` / `rust-toolchain.toml`).

## Commands

```bash
cargo test --manifest-path ax-bi-rust/Cargo.toml
cd ax-bi-rust/python
maturin build --interpreter python
cd ../python-genai
maturin build --interpreter python
```

When running Rust tests from a Python distribution that does not expose
`libpython` on the default dynamic library path, set the library path first. For
example, with a conda Python on macOS:

```bash
DYLD_LIBRARY_PATH="$CONDA_PREFIX/lib" cargo test --manifest-path ax-bi-rust/Cargo.toml
```

The Python wrappers live in `axbi/runtime_modernization/rust_sql.py` and
`axbi/runtime_modernization/rust_genai.py`. Use `RUST_SQL_KERNEL` or
`RUST_ASSET_RANKING_KERNEL` to opt in when the relevant extension is installed.
