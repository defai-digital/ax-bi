# AX BI Desktop Release

This document describes the CI/CD and Homebrew distribution pipeline for the
Tauri desktop shell. It follows the same trust model as **AX Studio** and
**AX Code Desktop**:

1. Apple Developer ID sign + notarize (macOS)
2. Publish installers to a GitHub Release
3. Detached **minisign** signatures on all assets
4. Automated Homebrew cask update for
   [defai-digital/homebrew-ax-bi](https://github.com/defai-digital/homebrew-ax-bi)

## Product naming

| Surface | Name |
| --- | --- |
| macOS app bundle / Dock / menu | **AX BI** (`AX BI.app`) |
| Windows product / installer | **AX BI** |
| Bundle identifier (stable) | `com.axbi.desktop` |
| Homebrew cask token | `ax-bi` |
| Release tag | `ax-bi-desktop-vX.Y.Z` |
| Primary macOS asset | `AX.BI_X.Y.Z_aarch64.dmg` |

`productName` / window title in `src-tauri/tauri.conf.json` must stay **AX BI**
so Gatekeeper, Homebrew, and the shell UI match.

## User install (macOS Apple Silicon)

```bash
brew install --cask defai-digital/ax-bi/ax-bi
```

Equivalent explicit form:

```bash
brew tap defai-digital/ax-bi https://github.com/defai-digital/homebrew-ax-bi
brew install --cask ax-bi
```

Upgrade:

```bash
brew upgrade --cask defai-digital/ax-bi/ax-bi
```

The cask installs **AX BI.app** and pulls Colima, Lima, Docker CLI, and Docker Compose
as formulas. The app manages the local AX BI runtime after install.

## Pipeline overview

```text
tag ax-bi-desktop-vX.Y.Z
  → draft GitHub Release
  → macOS arm64: codesign + notarytool + staple DMG
  → Windows: NSIS/MSI build
  → minisign all release assets
  → publish release
  → push Casks/ax-bi.rb to homebrew-ax-bi (SHA256 of DMG)
```

Workflow file: [`.github/workflows/ax-bi-desktop-release.yml`](../.github/workflows/ax-bi-desktop-release.yml)

## Required GitHub secrets

### DEFAI Apple Developer ID (this project)

Verified local signing identity:

```text
Developer ID Application: DEFAI PRIVATE LIMITED (N5ZUZDUJS6)
SHA-1: CCA480038EE61E7CB9DF9FAACD842EC06949CD79
```

| Item | Value | GitHub secret / notes |
| --- | --- | --- |
| Team ID | `N5ZUZDUJS6` | `APPLE_TEAM_ID` |
| App Store Connect Issuer ID | `3cdb065e-9d78-451f-8424-e1e6b1547d64` | `APPLE_API_ISSUER` or `NOTARY_ISSUER` |
| Codesign identity (resolved in CI) | `Developer ID Application: DEFAI PRIVATE LIMITED (N5ZUZDUJS6)` | Imported from `.p12`; not a separate secret |
| App Store Connect API Key ID | *(from Keys page, e.g. `ABC123DEFG`)* | `APPLE_API_KEY_ID` or `NOTARY_KEY_ID` — **still required** |
| API key file (`.p8`) | Download once from App Store Connect | `APPLE_API_KEY_B64` or `NOTARIZE_P8_BASE64` |
| Developer ID cert export (`.p12`) | Export from Keychain Access | `APPLE_CERTIFICATE` or `CODE_SIGN_P12_BASE64` + password secret |

The release workflow already asserts that the imported identity contains `(N5ZUZDUJS6)` when `APPLE_TEAM_ID` is set.

### Apple secrets (macOS, fail-closed)

| Secret | Purpose | DEFAI value / action |
| --- | --- | --- |
| `APPLE_TEAM_ID` | Team match for Developer ID | `N5ZUZDUJS6` |
| `APPLE_API_ISSUER` or `NOTARY_ISSUER` | App Store Connect issuer UUID | `3cdb065e-9d78-451f-8424-e1e6b1547d64` |
| `APPLE_CERTIFICATE` or `CODE_SIGN_P12_BASE64` | Developer ID Application `.p12` (base64) | Export cert + private key (see below) |
| `APPLE_CERTIFICATE_PASSWORD` or `CODE_SIGN_P12_PASSWORD` | P12 password | Choose at export time |
| `APPLE_API_KEY_B64` or `NOTARIZE_P8_BASE64` | Notary API key `.p8` (base64) | App Store Connect → Users and Access → Integrations → Keys |
| `APPLE_API_KEY_ID` or `NOTARY_KEY_ID` | Notary API key id | Same Keys page (10-char id) |

These names match AX Studio so org-level secrets can be reused when the same
Developer ID and notary key are shared across DEFAI apps.

### Export the Developer ID `.p12` for CI

On the Mac that already has the identity (the one that shows `N5ZUZDUJS6`):

1. Open **Keychain Access** → **login** (or the keychain holding the cert).
2. Find **Developer ID Application: DEFAI PRIVATE LIMITED (N5ZUZDUJS6)**.
3. Export as `.p12` (include private key); set a strong password.
4. Encode for GitHub:

```bash
base64 -i DeveloperID.p12 | pbcopy   # → APPLE_CERTIFICATE / CODE_SIGN_P12_BASE64
```

5. Store the export password as `APPLE_CERTIFICATE_PASSWORD` / `CODE_SIGN_P12_PASSWORD`.

Never commit the `.p12`, password, or `.p8` into the monorepo.

### Notary API key (App Store Connect)

1. [App Store Connect](https://appstoreconnect.apple.com/) → **Users and Access** → **Integrations** → **App Store Connect API**.
2. Create or reuse a key with **Developer** (or Admin) access suitable for notarization.
3. Note **Key ID** → `APPLE_API_KEY_ID` / `NOTARY_KEY_ID`.
4. Issuer is already known: `3cdb065e-9d78-451f-8424-e1e6b1547d64`.
5. Download the `.p8` once:

```bash
base64 -i AuthKey_XXXXXXXXXX.p8 | pbcopy   # → APPLE_API_KEY_B64 / NOTARIZE_P8_BASE64
```

### Minisign (fail-closed)

| Secret | Purpose |
| --- | --- |
| `AX_BI_MINISIGN_SECRET_KEY_B64` | Base64-encoded minisign secret key |
| `AX_BI_MINISIGN_PUBLIC_KEY` | Public key string (or full `.pub` file contents) |
| `AX_BI_MINISIGN_PASSWORD` | Passphrase for the encrypted secret key |

Pinned release public key (also in
[`docs/ax-bi.minisign.pub`](docs/ax-bi.minisign.pub)):

```text
RWQ4HnJ0rpYY0Oa0wt5Itv0ps4n8bkNhGqaOGotNzLnMRDeOr+mCljzk
```

Secret key material lives outside the monorepo (`~/signkey/ax-bi.minisign.key`)
and in GitHub Actions secrets. Do not commit the secret key or password.

Generate a replacement keypair only when rotating:

```bash
mkdir -p ~/signkey && chmod 700 ~/signkey
minisign -G -s ~/signkey/ax-bi.minisign.key -p ~/signkey/ax-bi.minisign.pub
# Store passphrase in Keychain (optional local signing):
security add-generic-password -U -a ax-bi-minisign -s ax-bi-minisign -w
# CI secret:
base64 < ~/signkey/ax-bi.minisign.key | pbcopy   # AX_BI_MINISIGN_SECRET_KEY_B64
```

Verify a downloaded asset:

```bash
minisign -Vm AX.BI_0.1.0_aarch64.dmg \
  -p ax-bi-desktop/docs/ax-bi.minisign.pub \
  -x AX.BI_0.1.0_aarch64.dmg.minisig
```

### Homebrew tap

| Secret | Purpose |
| --- | --- |
| `HOMEBREW_TAP_TOKEN` (or legacy `TAP_TOKEN`) | PAT with **write** to `defai-digital/homebrew-ax-bi` |

Do not use the default monorepo `GITHUB_TOKEN` for the tap; the workflow clones
and pushes with this dedicated token (same as Studio/Code).

The tap repo is live: [defai-digital/homebrew-ax-bi](https://github.com/defai-digital/homebrew-ax-bi).

### Secrets already configured on `defai-digital/ax-bi`

| Secret | Status |
| --- | --- |
| `APPLE_TEAM_ID` | Set (`N5ZUZDUJS6`) |
| `APPLE_API_ISSUER` / `NOTARY_ISSUER` | Set (`3cdb065e-9d78-451f-8424-e1e6b1547d64`) |
| `AX_BI_MINISIGN_*` (secret, public, password) | Set; public key in `docs/ax-bi.minisign.pub` |
| `HOMEBREW_TAP_TOKEN` | Set (write access to `defai-digital/homebrew-ax-bi`) |

### Secrets still required before the first release tag

Copy from **ax-studio** (same DEFAI Developer ID / notary key) or export fresh.
Local signing identity when present:

```text
Developer ID Application: DEFAI PRIVATE LIMITED (N5ZUZDUJS6)
SHA-1: CCA480038EE61E7CB9DF9FAACD842EC06949CD79
```

| Secret | Source |
| --- | --- |
| `APPLE_CERTIFICATE` or `CODE_SIGN_P12_BASE64` | Studio secret or Keychain `.p12` export |
| `APPLE_CERTIFICATE_PASSWORD` or `CODE_SIGN_P12_PASSWORD` | Matching p12 password |
| `APPLE_API_KEY_B64` or `NOTARIZE_P8_BASE64` | Studio notary `.p8` |
| `APPLE_API_KEY_ID` or `NOTARY_KEY_ID` | Studio Key ID |

```bash
# Example after you have the files/values locally:
gh secret set APPLE_CERTIFICATE -R defai-digital/ax-bi < cert.p12.b64
gh secret set APPLE_CERTIFICATE_PASSWORD -R defai-digital/ax-bi
gh secret set APPLE_API_KEY_B64 -R defai-digital/ax-bi < AuthKey.p8.b64
gh secret set APPLE_API_KEY_ID -R defai-digital/ax-bi
gh secret set HOMEBREW_TAP_TOKEN -R defai-digital/ax-bi
```

## Release steps (maintainers)

1. Ensure `main` is green for `ax-bi-desktop` checks.
2. Bump version if needed (workflow also runs `set-version.mjs` during build):

   ```bash
   cd ax-bi-desktop
   node scripts/release/set-version.mjs --version 0.1.0
   git add -A && git commit -m "chore(desktop): release 0.1.0"
   ```

3. Tag and push:

   ```bash
   git tag ax-bi-desktop-v0.1.0
   git push origin main ax-bi-desktop-v0.1.0
   ```

   Or run **AX BI Desktop Release** via `workflow_dispatch` with `version=0.1.0`.

4. Confirm the workflow:
   - Draft release created
   - macOS DMG notarized
   - Windows installers uploaded
   - `.minisig` files attached
   - Release published
   - `homebrew-ax-bi` cask updated

5. Smoke-test:

   ```bash
   brew uninstall --cask ax-bi 2>/dev/null || true
   brew untap defai-digital/ax-bi 2>/dev/null || true
   brew install --cask defai-digital/ax-bi/ax-bi
   open -a "AX BI"
   ```

## Local scripts

| Script | Role |
| --- | --- |
| `scripts/release/set-version.mjs` | Sync `tauri.conf.json`, `Cargo.toml`, `package.json` |
| `scripts/release/rename-release-assets.mjs` | Normalize `AX BI_*` → `AX.BI_*` asset names |
| `scripts/release/minisign-artifacts.mjs` | Sign / verify artifacts |
| `scripts/release/write-homebrew-cask.mjs` | Emit `Casks/ax-bi.rb` for the tap |
| `packaging/homebrew/Casks/ax-bi.rb.template` | Documented cask shape |

## Windows notes

- Product display name is **AX BI** (same Tauri `productName`).
- CI builds NSIS/MSI installers and attaches them to the GitHub Release.
- Authenticode signing can be added later (Azure Trusted Signing pattern from
  AX Code Desktop); unsigned Windows builds still publish with a warning in
  release notes until those secrets exist.
- Homebrew is macOS-only; Windows users download from GitHub Releases.

## Trust layers (do not collapse)

| Layer | Protects | Mechanism |
| --- | --- | --- |
| Apple notarization | Gatekeeper first launch | Developer ID + notarytool + staple |
| minisign | Download integrity | Detached `.minisig` on GitHub assets |
| Homebrew SHA256 | Cask install integrity | `sha256` in `Casks/ax-bi.rb` |

minisign does **not** replace notarization. Homebrew SHA256 does **not** replace
minisign for non-brew downloaders.
