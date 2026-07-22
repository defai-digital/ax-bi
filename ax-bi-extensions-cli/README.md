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

# ax-bi-extensions-cli

[![PyPI version](https://badge.fury.io/py/ax-bi-extensions-cli.svg)](https://badge.fury.io/py/ax-bi-extensions-cli)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/Apache-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

Official command-line interface for building, bundling, and managing AX BI extensions. This CLI tool provides developers with everything needed to create, develop, and package extensions for the AX BI ecosystem.

## 🚀 Features

- **Extension Scaffolding** - Generate initial folder structure and scaffold new extension projects
- **Validation** - Validate extension structure and configuration before building
- **Development Server** - Automatically rebuild extensions as files change during development
- **Build System** - Build extension assets for production deployment
- **Bundle Packaging** - Package extensions into distributable .supx files

## 📦 Installation

```bash
pip install ax-bi-extensions-cli
```

## 🛠️ Quick Start

### Available Commands

```bash
# Scaffold a new extension project (interactive prompts, or pass options directly)
ax-bi-extensions init [--publisher <publisher>] [--name <name>] [--display-name <name>]
                      [--version <version>] [--license <license>]
                      [--frontend/--no-frontend] [--backend/--no-backend]

# Validate extension structure and configuration
ax-bi-extensions validate

# Build extension assets for production (runs validate first)
ax-bi-extensions build

# Package extension into a distributable .supx file (runs build first)
ax-bi-extensions bundle [--output/-o <path>]

# Automatically rebuild extension as files change during development
ax-bi-extensions dev
```

## 📋 Extension Structure

The CLI scaffolds extensions with the following structure:

```
{publisher}.{name}/             # e.g., my-org.dashboard-widgets/
├── extension.json              # Extension configuration and metadata
├── .gitignore
├── frontend/                   # Optional frontend code
│   ├── src/
│   │   └── index.tsx           # Frontend entry point
│   ├── package.json
│   ├── webpack.config.js
│   └── tsconfig.json
└── backend/                    # Optional backend code
    ├── src/
    │   └── {publisher}/        # e.g., my_org/
    │       └── {name}/         # e.g., dashboard_widgets/
    │           └── entrypoint.py
    └── pyproject.toml
```

## 📄 License

Licensed under the Apache License, Version 2.0. See [LICENSE](https://github.com/defai-digital/ax-bi/blob/main/LICENSE.txt) for details.

## 🔗 Links

- [Community](https://github.com/defai-digital/ax-bi#community)
- [GitHub Repository](https://github.com/defai-digital/ax-bi)
- [Extensions Documentation](https://github.com/defai-digital/ax-bi/tree/main/docs/developer_docs/extensions/overview.md)
