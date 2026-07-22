#!/usr/bin/env bash
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
NOTARY_PROFILE="${AX_NOTARY_PROFILE:-ax-notary}"
DMG_PATH="${1:-}"

usage() {
  cat <<'EOF'
Usage: npm run release:notarize -- [DMG_PATH]

Submit a Developer ID-signed AX BI DMG to Apple's notary service, then staple
and validate the ticket. If DMG_PATH is omitted, the latest Tauri bundle path
is discovered automatically.

Environment:
  AX_NOTARY_PROFILE  notarytool Keychain profile (default: ax-notary)
EOF
}

fail() {
  echo "notarization error: $*" >&2
  exit 1
}

if [[ $# -gt 1 ]]; then
  usage >&2
  exit 2
fi
if [[ "$DMG_PATH" == "-h" || "$DMG_PATH" == "--help" ]]; then
  usage
  exit 0
fi

command -v xcrun >/dev/null 2>&1 || fail "xcrun is required"

if [[ -z "$DMG_PATH" ]]; then
  candidates=()
  for bundle_dir in \
    "${DESKTOP_DIR}/src-tauri/target/aarch64-apple-darwin/release/bundle/dmg" \
    "${DESKTOP_DIR}/src-tauri/target/x86_64-apple-darwin/release/bundle/dmg" \
    "${DESKTOP_DIR}/src-tauri/target/release/bundle/dmg"; do
    if [[ -d "$bundle_dir" ]]; then
      while IFS= read -r -d '' dmg; do
        candidates+=("$dmg")
      done < <(find "$bundle_dir" -maxdepth 1 -name '*.dmg' -print0 2>/dev/null)
    fi
  done

  if [[ ${#candidates[@]} -eq 0 ]]; then
    fail "no Tauri DMG found; pass its path explicitly"
  fi

  # Prefer the newest DMG by mtime when multiple exist.
  newest=""
  newest_mtime=0
  for dmg in "${candidates[@]}"; do
    mtime="$(stat -f '%m' "$dmg" 2>/dev/null || stat -c '%Y' "$dmg" 2>/dev/null || echo 0)"
    if [[ "$mtime" -ge "$newest_mtime" ]]; then
      newest_mtime="$mtime"
      newest="$dmg"
    fi
  done
  DMG_PATH="$newest"

  if [[ ${#candidates[@]} -gt 1 ]]; then
    echo "Multiple DMGs found; selecting newest by mtime:"
    for dmg in "${candidates[@]}"; do
      echo "  - $dmg"
    done
    echo "Using: $DMG_PATH"
  fi
fi

[[ -n "$DMG_PATH" ]] || fail "no Tauri DMG found; pass its path explicitly"
[[ -f "$DMG_PATH" ]] || fail "DMG not found: $DMG_PATH"
[[ -n "$NOTARY_PROFILE" ]] || fail "AX_NOTARY_PROFILE must not be empty"

echo "Notarizing $(basename "$DMG_PATH") with Keychain profile $NOTARY_PROFILE"
xcrun notarytool submit "$DMG_PATH" \
  --keychain-profile "$NOTARY_PROFILE" \
  --wait
xcrun stapler staple "$DMG_PATH"
xcrun stapler validate "$DMG_PATH"
spctl --assess --type install --verbose=2 "$DMG_PATH"

echo "Notarization complete: $DMG_PATH"
