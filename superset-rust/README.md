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

# Superset Rust Proof Of Concept

This workspace contains optional Rust kernels for AX-BI runtime modernization.
The first crate, `ax_sql`, exposes a narrow PyO3 helper for SQL whitespace
normalization. Superset imports it only when built and enabled; Python fallback
behavior remains available.

## Commands

```bash
cargo test --manifest-path superset-rust/Cargo.toml
cd superset-rust/python
maturin build --interpreter python
```

When running Rust tests from a Python distribution that does not expose
`libpython` on the default dynamic library path, set the library path first. For
example, with a conda Python on macOS:

```bash
DYLD_LIBRARY_PATH="$CONDA_PREFIX/lib" cargo test --manifest-path superset-rust/Cargo.toml
```

The Python wrapper lives in `superset/runtime_modernization/rust_sql.py`.
Use the `RUST_SQL_KERNEL` feature flag to opt in when the extension is installed.
