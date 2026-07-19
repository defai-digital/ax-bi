# winget package: DEFAI.AXBI

Windows counterpart to the Homebrew cask
[`defai-digital/homebrew-ax-bi`](https://github.com/defai-digital/homebrew-ax-bi).

| Field | Value |
| --- | --- |
| Package identifier | `DEFAI.AXBI` |
| Package name | AX BI |
| Publisher | DEFAI Private Limited |
| Installer types | NSIS (user scope) + MSI (machine scope) |
| Code signing | DigiCert Authenticode via Azure Key Vault (`cert-defai`) |
| Expected thumbprint (SHA-1) | `FC40F1109912C025E751E804AA9BD1538A2D12EF` |
| Generator | `scripts/release/write-winget-manifests.mjs` |

## User install (after community merge)

```powershell
winget install -e --id DEFAI.AXBI
winget upgrade -e --id DEFAI.AXBI
winget uninstall -e --id DEFAI.AXBI
```

Until the package is in
[microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs), install from
[GitHub Releases](https://github.com/defai-digital/ax-bi/releases) (signed
`AX.BI_*_x64-setup.exe` / `.msi`).

## How manifests are produced

The generator is the **source of truth** (same idea as
`write-homebrew-cask.mjs`). Static YAML files in this directory are examples
only and may drift; do not hand-edit them for a release.

### Local / dry-run

```bash
cd ax-bi-desktop
# With downloaded release assets (NSIS + MSI):
node scripts/release/write-winget-manifests.mjs   --version 0.1.0   --artifact-dir /path/to/assets   --out-dir /tmp/winget-out

# Or with explicit hashes:
node scripts/release/write-winget-manifests.mjs   --version 0.1.0   --nsis-name AX.BI_0.1.0_x64-setup.exe   --nsis-sha256 <64-hex>   --msi-name AX.BI_0.1.0_x64_en-US.msi   --msi-sha256 <64-hex>   --out-dir /tmp/winget-out
```

Output layout:

```text
manifests/d/DEFAI/AXBI/<version>/
  DEFAI.AXBI.yaml
  DEFAI.AXBI.installer.yaml
  DEFAI.AXBI.locale.en-US.yaml
```

Asset discovery accepts Tauri locale suffixes on MSI names
(e.g. `AX.BI_0.1.0_x64_en-US.msi` as well as `AX.BI_0.1.0_x64.msi`).

### CI (desktop release)

After `publish-release`, the `prepare-winget-manifests` job:

1. Downloads the published x64 NSIS + MSI from the GitHub Release
2. Verifies each with **minisign** (fail-closed)
3. Runs `write-winget-manifests.mjs`
4. Attaches `AX.BI_<version>_winget-manifests.zip` to the release
5. Uploads a workflow artifact for inspection

Skip with workflow input `skip_winget=true`. Missing winget automation never
blocks macOS/Homebrew; this job only runs after a successful publish.

There is **no** automatic PR to `microsoft/winget-pkgs` in v1 (community
review required). Submit from the release zip.

## Submit to winget-pkgs (maintainer)

1. Download `AX.BI_<version>_winget-manifests.zip` from the desktop release.
2. Unzip so you have `manifests/d/DEFAI/AXBI/<version>/…`.
3. Fork [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs).
4. Copy that version folder into the fork at the same path.
5. On Windows, validate:

   ```powershell
   winget validate --manifest manifests\d\DEFAI\AXBI\<version>
   winget install --manifest manifests\d\DEFAI\AXBI\<version>
   ```

6. Open a PR following the
   [winget-pkgs checklist](https://github.com/microsoft/winget-pkgs/blob/master/doc/README.md).

Notes for reviewers:

- Installers are **Authenticode-signed** by DEFAI Private Limited (DigiCert).
- Publisher website: `https://github.com/defai-digital`
- License: Apache-2.0
- Local **Run locally** still needs Docker Desktop (optional; not a winget
  dependency): `winget install -e --id Docker.DockerDesktop`

## Trust

| Layer | Mechanism |
| --- | --- |
| Publisher | Authenticode (Key Vault); do not put the DigiCert PFX in CI |
| Download integrity | minisign on release assets (verified before hashing for winget) |
| winget integrity | `InstallerSha256` in generated installer manifest |

## npm

```bash
npm run release:write-winget -- --version 0.1.0 --artifact-dir ./assets --out-dir ./winget-out
npm run test:winget-manifests
```
