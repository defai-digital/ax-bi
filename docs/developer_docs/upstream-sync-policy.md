---
title: Upstream Sync Policy
sidebar_position: 3
---

<!--
This product is derived from Apache Superset, which is licensed to the
Apache Software Foundation (ASF) under one or more contributor license
agreements.  See the NOTICE file distributed with this work for additional
information regarding copyright ownership.  The ASF licenses the underlying
work to you under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License.  You may obtain a
copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
License for the specific language governing permissions and limitations
under the License.
-->

# Upstream Sync Policy

AX BI is derived from Apache Superset. Staying close to upstream Superset is
important for security, dependency health, database compatibility, dashboard and
SQL Lab reliability, and long-term maintainability.

AX BI must not merge upstream changes blindly. Upstream work can touch the same
surfaces AX BI extends for MCP, GenAI BI, semantic metadata, local upload,
desktop integration, and product-specific UI. Every upstream sync must be
controlled, reviewed, tested, and documented.

## Policy

AX BI regularly merges Superset security fixes, bug fixes, dependency updates,
and stable release branches. Large features, architectural rewrites, and
breaking changes are selective and require explicit review.

The goal is not to merge every upstream pull request. The goal is to keep AX BI
close to stable Superset releases while isolating AX BI-specific work into
extensions, sidecars, MCP modules, and narrow fork patches wherever possible.

## Priority Matrix

| Upstream change type | Merge policy | Priority |
| --- | --- | --- |
| Security fix | Always merge or cherry-pick | Immediate |
| Critical bug fix | Usually merge or cherry-pick | High |
| Dependency CVE fix | Merge with CI and staging validation | High |
| Dashboard or chart bug fix | Usually merge | High |
| SQL Lab or database fix | Usually merge | High |
| Metadata migration fix | Merge only with migration testing | High |
| Extension framework improvement | Evaluate deeply; prefer adoption where it reduces fork patches | Medium-high |
| New chart type | Optional | Medium |
| UI redesign | Selective | Medium-low |
| Experimental feature | Usually skip | Low |
| Large architecture refactor | Review through a migration plan | Risky |
| Breaking API change | Only with an AX BI compatibility plan | Risky |

## Always Prioritize

Merge or cherry-pick these changes as soon as practical:

- Authentication and session security fixes
- Authorization, RBAC, RLS, and embedded guest-token fixes
- SQL execution safety and SQL parsing fixes
- Dependency CVE fixes for Python, Flask, Flask-AppBuilder, SQLAlchemy, React,
  and build tooling
- Database credential handling fixes
- Export, report, alert, and screenshot security fixes

## Usually Merge

These areas should normally be merged after test validation:

- Dashboard loading and rendering fixes
- Explore and chart rendering fixes
- SQL Lab reliability fixes
- Database connection and engine-spec fixes
- Metadata migration fixes
- Alerts, reports, cache, filter, and permission behavior fixes
- Frontend crash fixes

## Review Carefully

These areas often overlap with AX BI product work and require deeper review:

- Dashboard layout rewrites
- Explore control refactors
- Chart plugin architecture changes
- Frontend state-management rewrites
- Permission model rewrites
- Metadata schema changes
- Large dependency upgrades
- Experimental upstream features
- Breaking REST API, embedded SDK, or plugin API changes

## Branch Model

Use this branch model for upstream work:

| Branch | Purpose |
| --- | --- |
| `main` | AX BI product development and release-ready integration |
| `upstream-sync/<superset-version>` | Controlled merge from an Apache Superset release branch or tag |
| `ax-bi-stable` | Tested AX BI release candidate branch, when needed |
| `hotfix/<topic>` | Urgent security or production bug fixes |

Prefer upstream release branches and tags over random upstream pull requests.
Cherry-pick individual fixes only when the risk of waiting for the next full
sync is higher than the cherry-pick risk.

## Sync Process

1. Identify the current AX BI base commit or last upstream sync point.
2. Identify the target Superset release tag, release branch, or security fix.
3. Produce a gap report before merging.
4. Create an `upstream-sync/<superset-version>` branch.
5. Merge the target release branch or cherry-pick the selected fixes.
6. Resolve conflicts without dropping AX BI-specific behavior.
7. Run backend, frontend, MCP, and migration checks.
8. Validate core AX BI workflows in staging.
9. Document conflict decisions and skipped upstream changes.
10. Merge to `main` only after review.

## Gap Report

Every upstream sync should answer:

- Which Superset release/tag is AX BI being compared against?
- Which security fixes are missing?
- Which dependency updates are missing?
- Which dashboard, Explore, SQL Lab, database, migration, and reporting fixes
  are missing?
- Which upstream changes touch AX BI custom areas?
- Which files conflict?
- Which migrations are new or changed?
- Which changes are intentionally skipped, and why?

Useful commands:

```bash
git remote add apache https://github.com/apache/superset.git
git fetch apache --tags

git merge-base origin/main apache/<release-branch>
git rev-list --left-right --count origin/main...apache/<release-branch>
git log --oneline origin/main..apache/<release-branch>
git diff --name-status origin/main...apache/<release-branch>
```

Replace `<release-branch>` with the target upstream branch or compare directly
against a release tag such as `6.1.0` when appropriate.

## AX BI Regression Areas

After every upstream sync, validate at least:

- MCP service startup, tool registration, authentication, and authorization
- MCP dataset, chart, dashboard, SQL Lab, and AI tools
- Prompt-to-chart and prompt-to-dashboard flows
- Local file upload and dataset creation
- Dataset metadata, semantic context, and asset search
- Dashboard view, edit, native filters, cross-filters, and exports
- Explore chart creation and chart plugin rendering
- SQL Lab query execution, save, history, and permissions
- Reports, alerts, screenshots, and cache behavior
- Embedded dashboard and guest-token behavior
- `ax-services` health, readiness, contracts, and Superset connectivity
- Desktop shell deep links and web-app loading, when relevant

## Modularity Requirement

When an upstream sync conflicts with AX BI behavior, first ask whether the AX BI
behavior can move out of forked Superset core and into:

- MCP service modules
- `superset-core` shared abstractions
- Superset extension APIs
- `ax-services`
- Frontend extension points
- Narrow adapter layers

Deep fork patches are allowed only when they are necessary and documented.

## References

- Apache Superset GitHub releases: https://github.com/apache/superset/releases
- Apache Superset 6.0 release summary:
  https://preset.io/blog/apache-superset-6-0-release/
- Apache Superset 6.1 release summary:
  https://preset.io/blog/apache-superset-6-1-release/
