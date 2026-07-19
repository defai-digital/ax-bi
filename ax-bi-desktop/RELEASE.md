# AX BI Desktop Release

This document describes the CI/CD and Homebrew distribution pipeline for the
Tauri desktop shell. It follows the same trust model as **AX Studio** and
**AX Code Desktop**:

1. Apple Developer ID sign + notarize (macOS)
2. Azure Key Vault Authenticode sign (Windows)
3. Publish installers to a GitHub Release
4. Detached **minisign** signatures on all assets
5. Automated Homebrew cask update for
   [defai-digital/homebrew-ax-bi](https://github.com/defai-digital/homebrew-ax-bi)
6. Generate winget manifests (`DEFAI.AXBI`) from minisign-verified Windows
   installers and attach `AX.BI_*_winget-manifests.zip` to the release

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
  → Windows: Key Vault sign app executable + NSIS/MSI installers
  → minisign all release assets
  → re-download and verify Apple trust + minisign coverage
  → publish release
  → verify DMG minisign, then push Casks/ax-bi.rb (SHA256 of DMG)
  → verify Windows installers with minisign, write winget manifests, attach zip
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

### Local Apple signing and notarization

Local builds use the Developer ID Application certificate from the login
Keychain and the `ax-notary` notarytool profile. Store the notarization
credential once; omitting `--password` keeps the app-specific password out of
shell history and prompts for it securely:

```bash
xcrun notarytool store-credentials ax-notary \
  --apple-id "<apple-id>" \
  --team-id "N5ZUZDUJS6"
```

Build with the Developer ID identity, then submit, staple, and validate the
DMG. The helper discovers the normal Tauri output path when no path is passed:

```bash
export APPLE_SIGNING_IDENTITY="Developer ID Application: DEFAI PRIVATE LIMITED (N5ZUZDUJS6)"
npm run build -- --target aarch64-apple-darwin
npm run release:notarize
```

Set `AX_NOTARY_PROFILE` only when using a profile name other than `ax-notary`.
The Keychain profile contains the notarization credential; a plaintext password
file is not required by the release scripts.

### Windows Authenticode signing (Azure Key Vault, fail-closed)

The Windows release job uses AzureSignTool `7.0.1`. The private key remains in
Azure Key Vault; the exported PFX is an offline backup and must not be committed
or uploaded to GitHub Actions.

| Item | Value |
| --- | --- |
| Key Vault URL | `https://keyvault-defai.vault.azure.net` |
| Certificate name | `cert-defai` |
| Subject | `C=SG, L=Singapore, O=DEFAI Private Limited, CN=DEFAI Private Limited` |
| Issuer | `DigiCert Trusted G4 Code Signing RSA4096 SHA384 2021 CA1` |
| SHA-1 thumbprint | `FC40F1109912C025E751E804AA9BD1538A2D12EF` |
| Validity | 2026-07-13 through 2027-07-12 (UTC) |

Required GitHub Actions secrets:

| Secret | Value / purpose |
| --- | --- |
| `AZURE_TENANT_ID` | `0326d2a2-f46c-4673-a165-f49e712d0864` |
| `AZURE_CLIENT_ID` | `cbdd6dd3-0c59-43ec-8813-cd5b120eaf4c` |
| `AZURE_CLIENT_SECRET` | Repository service-principal secret; expires 2027-07-14 |

The service principal needs certificate read and key-sign permissions on
`keyvault-defai`. The RBAC vault grants `Key Vault Certificate User` and `Key
Vault Crypto User` to the signing principal at the vault scope. For a legacy
access-policy vault, grant Certificates `Get` plus Keys `Get` and `Sign`.

The workflow builds and signs `axbi-desktop.exe` before bundling so the
installed application is signed. It then signs the generated MSI and NSIS
installers, and verifies every signature against the pinned thumbprint. Missing
credentials, signing failures, invalid signatures, or a certificate mismatch
stop the release.

Service Principal + Client Secret is the configured authentication method.
GitHub OIDC is preferred for a future credentialless migration.

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
RWSlDu++afxCz01OqhYWhfo8+L8pVbSYXJBEb2zoWBuK0WACIzbGVZRO
```

Secret key material lives outside the monorepo. Local signing uses the shared AX
keypair at `~/signkey/ax.minisign.key` (an optional symlink to `ax.sec`) and
`~/signkey/ax.pub`. CI uses the same keypair through GitHub Actions secrets. Do
not commit the secret key or password.

Generate a replacement keypair only when rotating:

```bash
mkdir -p ~/signkey && chmod 700 ~/signkey
minisign -G -s ~/signkey/ax.sec -p ~/signkey/ax.pub
ln -sfn ax.sec ~/signkey/ax.minisign.key
# Store passphrase in Keychain (optional local signing):
security add-generic-password -U -a ax-release -s ax-minisign -w
```

When rotating the shared key, update all three GitHub Actions secrets together.
The password command prompts securely when no value is piped to it:

```bash
base64 < ~/signkey/ax.minisign.key | \
  gh secret set AX_BI_MINISIGN_SECRET_KEY_B64 -R defai-digital/ax-bi
gh secret set AX_BI_MINISIGN_PUBLIC_KEY -R defai-digital/ax-bi \
  < ~/signkey/ax.pub
gh secret set AX_BI_MINISIGN_PASSWORD -R defai-digital/ax-bi
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
| `AX_BI_MINISIGN_*` (secret, public, password) | Must match the shared key pinned in `docs/ax-bi.minisign.pub` |
| `HOMEBREW_TAP_TOKEN` | Set (write access to `defai-digital/homebrew-ax-bi`) |
| `AZURE_TENANT_ID` | Set (`0326d2a2-f46c-4673-a165-f49e712d0864`) |
| `AZURE_CLIENT_ID` | Set (`cbdd6dd3-0c59-43ec-8813-cd5b120eaf4c`) |
| `AZURE_CLIENT_SECRET` | Set; repository credential expires 2027-07-14 |

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
1b. Confirm GHCR has `ghcr.io/defai-digital/ax-bi:<version>` and
   `ghcr.io/defai-digital/ax-bi-services:<version>` (from the server image
   `v*` workflow). Desktop local runtimes pin to these tags in release builds.
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
| `scripts/release/write-winget-manifests.mjs` | Emit winget multi-file manifests (`DEFAI.AXBI`) |
| `packaging/homebrew/Casks/ax-bi.rb.template` | Documented cask shape |
| `packaging/winget/` | winget manifest templates (`DEFAI.AXBI`) |

## Windows notes

- Product display name is **AX BI** (same Tauri `productName`).
- CI signs the application executable before packaging, then signs and verifies
  both the NSIS and MSI installers before attaching them to the GitHub Release.
- Stable releases fail closed if the Azure signing credentials are absent, a
  signature is invalid, or the signer thumbprint differs from the pinned DEFAI
  certificate.
- **Do not** put the DigiCert PFX in GitHub Actions or treat it as an Apple
  codesign identity. The PFX is an offline backup of Key Vault `cert-defai`;
  production signing is AzureSignTool against the vault only.
- Homebrew is macOS-only. Windows users install from GitHub Releases (signed
  NSIS/MSI) or, once published, `winget install -e --id DEFAI.AXBI`.
- winget manifests are **generated in CI** after publish
  (`prepare-winget-manifests`): minisign-verify NSIS+MSI →
  `write-winget-manifests.mjs` → attach `AX.BI_*_winget-manifests.zip`.
  Opening a PR to `microsoft/winget-pkgs` remains a **manual** maintainer step
  (see [`packaging/winget/README.md`](packaging/winget/README.md)).
  Skip with workflow input `skip_winget`.
- For **Run locally**, document Docker Desktop separately
  (`winget install -e --id Docker.DockerDesktop`). Do not list Docker Desktop as
  a hard winget package dependency.

## Trust layers (do not collapse)

| Layer | Protects | Mechanism |
| --- | --- | --- |
| Apple notarization | Gatekeeper first launch | Developer ID + notarytool + staple |
| Windows Authenticode | SmartScreen / publisher trust | DigiCert code signing via Azure Key Vault (`cert-defai`, thumbprint `FC40F110…`) |
| minisign | Download integrity | Detached `.minisig` on GitHub assets |
| Homebrew SHA256 | Cask install integrity | `sha256` in `Casks/ax-bi.rb` |
| winget InstallerSha256 | winget install integrity | SHA-256 in `DEFAI.AXBI.installer.yaml` |

minisign does **not** replace notarization or Authenticode. Homebrew SHA256 does
**not** replace minisign for non-brew downloaders. winget SHA-256 does **not**
replace Authenticode publisher trust.
