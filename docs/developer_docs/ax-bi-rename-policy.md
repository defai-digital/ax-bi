---
title: AX BI Rename Policy
sidebar_position: 4
---

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

# AX BI Rename Policy

AX BI uses a clean-break product namespace. The project is independently
maintained by DEFAI Private Limited and does not provide aliases for the former
product name, package names, commands, routes, environment variables, or
extension scopes.

## Canonical Names

| Surface | Name or identifier |
| --- | --- |
| Product display name | `AX BI` |
| Python and JavaScript namespace | `axbi` |
| Python class prefix | `AxBI` |
| Repository and filesystem slug | `ax-bi` |
| Main CLI command | `ax-bi` |
| MCP wrapper command | `ax-bi-mcp` |
| Extension CLI command | `ax-bi-extensions` |
| Backend package | `axbi` |
| Shared Python package | `axbi_core` in `ax-bi-core/` |
| Frontend workspace directory | `ax-bi-frontend/` |
| Frontend package scope | `@ax-bi/*` |
| Route prefix | `/ax-bi` |
| Docker image | `ghcr.io/defai-digital/ax-bi` |
| Helm chart | `helm/ax-bi` |
| Repository links | `https://github.com/defai-digital/ax-bi` |
| User-Agent header | `AX-BI` |

`/api/v1/*` remains the REST API root because it is a protocol path rather than
a product-name namespace.

## Clean-Break Rules

- Do not add compatibility imports, command aliases, route redirects, package
  aliases, environment-variable fallbacks, or dual-published packages for the
  former namespace.
- New deployment configuration uses `AXBI_*` variables, except the canonical
  secret and test controls `AX_BI_SECRET_KEY` and `AX_BI_TESTENV`.
- Current code, tests, fixtures, generated metadata, package manifests, CI,
  containers, and release artifacts must use the canonical names above.
- The former product name is permitted only in legal notices, attribution,
  historical release notes, and documentation that explicitly discusses the
  upstream project or migration history.
- References to the upstream project must not be executable examples or imply
  runtime compatibility.

Run `python scripts/check_axbi_branding.py` before committing. The check rejects
former-name tokens in runtime and build surfaces while allowing documentation
and legal attribution.
