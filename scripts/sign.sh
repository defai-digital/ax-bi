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

SECRET_KEY="${AX_MINISIGN_SECRET_KEY:-${HOME}/signkey/ax.minisign.key}"
PUBLIC_KEY="${AX_MINISIGN_PUBLIC_KEY:-${HOME}/signkey/ax.pub}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PINNED_PUBLIC_KEY="${AX_MINISIGN_PINNED_PUBLIC_KEY:-${SCRIPT_DIR}/../ax-bi-desktop/docs/ax-bi.minisign.pub}"
KEYCHAIN_SERVICE="${AX_MINISIGN_KEYCHAIN_SERVICE:-ax-minisign}"
KEYCHAIN_ACCOUNT="${AX_MINISIGN_KEYCHAIN_ACCOUNT:-ax-release}"
FORCE=false
ARTIFACT=""

usage() {
  cat <<'EOF'
Usage: ./scripts/sign.sh [OPTIONS] <FILE_NAME>

Create and verify a detached minisign signature plus a SHA-512 checksum.

Options:
  --secret-key <path>  Secret key (default: ~/signkey/ax.minisign.key)
  --public-key <path>  Public key (default: ~/signkey/ax.pub)
  --pinned-public-key <path>
                       Expected release public key
  --force              Replace an existing .minisig file
  -h, --help           Show this help

Environment:
  AX_MINISIGN_SECRET_KEY  Override the default secret key path
  AX_MINISIGN_PUBLIC_KEY  Override the default public key path
  AX_MINISIGN_PINNED_PUBLIC_KEY
                           Override the pinned public key path
  AX_BI_MINISIGN_PASSWORD or MINISIGN_PASSWORD
                           Supply the secret-key passphrase non-interactively
  AX_MINISIGN_KEYCHAIN_SERVICE
                           Keychain service (default: ax-minisign)
  AX_MINISIGN_KEYCHAIN_ACCOUNT
                           Keychain account (default: ax-release)
EOF
}

fail() {
  echo "minisign error: $*" >&2
  exit 1
}

path_mode() {
  stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1" 2>/dev/null || true
}

require_private_path() {
  local path="$1"
  local label="$2"
  local mode
  mode="$(path_mode "$path")"
  [[ -n "$mode" ]] || fail "could not inspect permissions for $label: $path"
  if (( 8#$mode & 8#077 )); then
    fail "$label must not be group/world accessible: $path has mode $mode"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --secret-key)
      shift
      [[ -n "${1:-}" ]] || fail "--secret-key requires a path"
      SECRET_KEY="$1"
      ;;
    --public-key)
      shift
      [[ -n "${1:-}" ]] || fail "--public-key requires a path"
      PUBLIC_KEY="$1"
      ;;
    --pinned-public-key)
      shift
      [[ -n "${1:-}" ]] || fail "--pinned-public-key requires a path"
      PINNED_PUBLIC_KEY="$1"
      ;;
    --force)
      FORCE=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      fail "unknown option: $1"
      ;;
    *)
      [[ -z "$ARTIFACT" ]] || fail "only one artifact may be signed at a time"
      ARTIFACT="$1"
      ;;
  esac
  shift
done

[[ -n "$ARTIFACT" ]] || { usage >&2; exit 2; }
command -v minisign >/dev/null 2>&1 || fail "minisign is required"
command -v shasum >/dev/null 2>&1 || fail "shasum is required"
[[ -f "$ARTIFACT" ]] || fail "artifact not found: $ARTIFACT"
[[ -f "$SECRET_KEY" ]] || fail "secret key not found: $SECRET_KEY"
[[ -f "$PUBLIC_KEY" ]] || fail "public key not found: $PUBLIC_KEY"
[[ -f "$PINNED_PUBLIC_KEY" ]] || fail "pinned public key not found: $PINNED_PUBLIC_KEY"
require_private_path "$SECRET_KEY" "secret key"
require_private_path "$(dirname "$SECRET_KEY")" "secret key directory"

SELECTED_PUBLIC_KEY="$(awk '/^RW/ { print $1; exit }' "$PUBLIC_KEY")"
EXPECTED_PUBLIC_KEY="$(awk '/^RW/ { print $1; exit }' "$PINNED_PUBLIC_KEY")"
[[ -n "$SELECTED_PUBLIC_KEY" && -n "$EXPECTED_PUBLIC_KEY" ]] || \
  fail "selected or pinned minisign public key is malformed"
[[ "$SELECTED_PUBLIC_KEY" == "$EXPECTED_PUBLIC_KEY" ]] || \
  fail "public key does not match pinned release key: $PINNED_PUBLIC_KEY"

SIGNATURE="${ARTIFACT}.minisig"
if [[ -e "$SIGNATURE" && "$FORCE" != true ]]; then
  fail "signature already exists: $SIGNATURE (pass --force to replace it)"
fi
if [[ "$FORCE" == true ]]; then
  rm -f "$SIGNATURE"
fi

DIGEST="$(shasum -a 256 "$ARTIFACT" | awk '{print $1}')"
SIGNED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TRUSTED_COMMENT="AX BI release $(basename "$ARTIFACT") sha256=${DIGEST} signed=${SIGNED_AT}"
SIGN_ARGS=(
  -S
  -s "$SECRET_KEY"
  -m "$ARTIFACT"
  -x "$SIGNATURE"
  -c "AX BI minisign signature"
  -t "$TRUSTED_COMMENT"
)

PASSWORD="${AX_BI_MINISIGN_PASSWORD:-${MINISIGN_PASSWORD:-}}"
if [[ -z "$PASSWORD" && "$(uname -s)" == "Darwin" ]] && \
  command -v security >/dev/null 2>&1; then
  PASSWORD="$(
    security find-generic-password \
      -s "$KEYCHAIN_SERVICE" \
      -a "$KEYCHAIN_ACCOUNT" \
      -w 2>/dev/null || true
  )"
fi
if [[ -n "$PASSWORD" ]]; then
  printf '%s\n' "$PASSWORD" | minisign "${SIGN_ARGS[@]}"
else
  minisign "${SIGN_ARGS[@]}"
fi

minisign -Vm "$ARTIFACT" -p "$PUBLIC_KEY" -x "$SIGNATURE"
shasum -a 512 "$ARTIFACT" > "${ARTIFACT}.sha512"
