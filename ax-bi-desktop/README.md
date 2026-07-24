# AX BI Desktop Client

A thin desktop client for the AX BI data visualization and analytics platform, built with [Tauri v2](https://tauri.app/).

## Overview

AX BI Desktop delivers a native desktop experience for the AX BI web application through two complementary layers:

### Phase 1 — Desktop-Grade UX (in the web app)

These features live in `ax-bi-frontend/` and work in both the browser and the Tauri shell:

- **Command palette** — `⌘K` / `Ctrl+K` fuzzy-search across all navigation and actions
- **Global keyboard shortcuts** — OS-aware shortcut registry with help overlay
- **Service worker** — Offline-capable caching (stale-while-revalidate for assets, network-first for API)
- **PWA platform support** — Browser-managed installation and file handling remain available without an in-app install promotion

### Phase 2 — Tauri Desktop Shell

These features live in `ax-bi-desktop/` and require the native app:

- **Native window** — Standalone desktop shell for local or hosted AX BI
- **First-run home** — Run a local Docker instance or connect to a remote server (ops controls stay under Advanced)
- **Full-bleed BI** — Once open, the web app fills the window (no extra desktop top bar)
- **Desktop actions in web Settings** — Desktop home / Desktop settings (also ⌘, / ⌘⇧H)
- **Settings drawer** — Local instance, remote connection, theme; runtime logs/deps behind Advanced
- **Deep links** — `axbi://dashboard/{id}`, `axbi://chart/{id}` open directly in the app
- **System tray** — Quick access to dashboards and SQL Lab (infrastructure in place)
- **Supported release targets** — macOS Apple Silicon (arm64) and Windows x64 via GitHub Actions

## Architecture

The desktop client is a **thin shell** with a bundled product launcher. It does
**not** bundle the Python backend, database drivers, or any server-side
components. The home screen offers two primary paths: run a local Docker-based
instance (app-managed Colima on macOS, Docker Engine on Windows), or connect to
a hosted AX BI server. Engine/Docker status, logs, and prepare/stop/update
controls live under
**Settings → Advanced runtime**.

## Install and first use

AX BI Desktop is a window for an AX BI server. After installing it, choose one
of these paths:

| If you want to… | Choose in AX BI Desktop | What you need |
| --- | --- | --- |
| Use your organisation's existing AX BI deployment | **Connect to server** | The server address from your administrator, such as `https://bi.example.com` |
| Run AX BI on your own Windows PC | **Run locally** | Docker Desktop installed and running |

You do not need to clone this repository, install Python, or use a terminal to
use the released desktop app.

### Windows

1. Download the signed Windows installer from
   [GitHub Releases](https://github.com/defai-digital/ax-bi/releases). Choose
   either `AX.BI_*_x64-setup.exe` (recommended) or the `.msi` installer.
2. Open the downloaded file and follow the Windows installer prompts. Verify
   that the publisher is **DEFAI Private Limited** if Windows displays a
   publisher prompt.
3. Open **AX BI** from the Start menu.
4. On the welcome screen, select one of the following:

   - **Connect to server:** enter the complete address supplied by your AX BI
     administrator, including `https://`, then select **Connect**. Sign in with
     your usual AX BI account.
   - **Run locally:** install Docker Desktop once, start Docker Desktop, then
     select **Run locally**. AX BI downloads and starts its local services; the
     first start can take a few minutes. When the login screen opens, use the
     generated local admin credentials shown by AX BI.

To install Docker Desktop for a local instance, run this in PowerShell, or use
[Docker's Windows installer](https://docs.docker.com/desktop/setup/install/windows-install/):

```powershell
winget install -e --id Docker.DockerDesktop
```

If Docker is already installed but AX BI cannot start locally, open Docker
Desktop and wait until it reports that the engine is running, then return to AX
BI and try again. For a hosted server, Docker is not needed.

### macOS

Install AX BI with Homebrew:

```bash
brew install --cask defai-digital/ax-bi/ax-bi
```

Open **AX BI** from Applications and choose **Connect to server** or **Run
locally** on the welcome screen. The local path manages its required runtime;
the hosted-server path only needs the server address and your usual account.

### After setup

- To return to the welcome screen or change the server, open **Settings →
  Desktop home**.
- To view the generated credentials for a local instance, use **Settings →
  Advanced → Credentials**.
- The desktop app remembers a server address you entered, but it does not
  automatically reconnect to it when launched.

## Packaging and release details

macOS app name (Dock / Applications / menu bar): **AX BI** (`AX BI.app`).
Windows product name: **AX BI** (same Tauri `productName`).

The intended macOS user path is the Homebrew tap at
[defai-digital/homebrew-ax-bi](https://github.com/defai-digital/homebrew-ax-bi):

```bash
brew install --cask defai-digital/ax-bi/ax-bi
```

That one-liner taps `https://github.com/defai-digital/homebrew-ax-bi` and installs
the `ax-bi` cask. Equivalent explicit form:

```bash
brew tap defai-digital/ax-bi https://github.com/defai-digital/homebrew-ax-bi
brew install --cask ax-bi
```

After installation, AX BI should guide the user to either connect to an existing
server or start a local runtime. The local runtime manager uses Colima (macOS) or
Docker Engine (Windows) with the same Compose stack so users do not need to clone
this repository or run Docker by hand. The macOS cask installs Colima, Lima,
Docker CLI, and Docker Compose automatically; install them manually only when
using the standalone DMG:

```bash
brew install colima lima docker docker-compose
```

When the winget package is published:

```powershell
winget install -e --id DEFAI.AXBI
```

Manifest templates: [packaging/winget/](packaging/winget/README.md).

See [LOCAL_RUNTIME.md](LOCAL_RUNTIME.md) for runtime architecture and
[RELEASE.md](RELEASE.md) for CI/CD, Apple signing, Windows Authenticode (Azure
Key Vault), minisign, Homebrew, and winget packaging.

```
┌─────────────────────────────────────────────────────────────────┐
│                     AX BI Desktop Client                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   Tauri WebView                            │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │          AX BI Web Application                       │  │  │
│  │  │                                                       │  │  │
│  │  │  ┌─────────────────┐  ┌──────────────────────────┐  │  │  │
│  │  │  │ ShortcutProvider │  │ CommandPaletteProvider   │  │  │  │
│  │  │  │ (⌘K, ⌘/, ...)   │  │ (fuzzy search, commands) │  │  │  │
│  │  │  └─────────────────┘  └──────────────────────────┘  │  │  │
│  │  │                                                       │  │  │
│  │  │  Service Worker · PWA Support · Keyboard Shortcuts   │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Native: Deep Links (axbi://) · System Tray · Notifications     │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- **Node.js**: See `ax-bi-frontend/package.json` `engines` field (24.x+)
- **Rust**: 1.75 or later (via [rustup](https://rustup.rs/))
- **Platform-specific dependencies**:
  - **macOS**: Xcode Command Line Tools
  - **Windows**: WebView2 (included in Windows 10/11)
  - **Linux**: See [Tauri v2 prerequisites](https://v2.tauri.app/start/prerequisites/)

## Development

### 1. Launch the Tauri desktop shell

Run from the **desktop package directory** (not the monorepo root — there is no
root `npm run dev` for this app):

```bash
cd ax-bi-desktop
npm install           # First time only
npm run dev           # Builds Rust + launches native window
```

The first `cargo` build can take several minutes. When the window opens:

1. **Run locally** — prepares/starts the app-managed engine + Docker Compose
   stack (Colima on macOS, Docker Desktop on Windows), or
2. **Connect to server** — paste a hosted AX BI URL

When local AX BI is healthy, the shell opens the web app full-bleed and shows a
**Local admin login** toast (also under Settings → Advanced → Credentials).

Generated local login:

- username: `admin`
- password: shown on first run and under Settings → Advanced → Credentials

### 2. Optional local backend

```bash
ax-bi run -p 31423 --with-threads --reload --debugger
```

The launcher can also start the app-managed local Docker runtime.

### Build for production

```bash
npm run build         # Release build with a macOS app bundle
npm run build:debug   # Debug build (faster, larger)
```

Output locations:
- **macOS app**: `src-tauri/target/release/bundle/macos/`

## Configuration

### Server URL

By default the Tauri shell loads the bundled launcher from `src/index.html`.
Use the launcher Connect form for hosted AX BI instances.

Local AX BI opens in a separate persistent webview at its loopback URL. Keeping
the local web app top-level makes its login cookie first-party and avoids WebKit
session loops caused by embedding the local server in the launcher iframe.

### Deep Links

The desktop client registers the `axbi://` URL scheme. Supported patterns:

| Deep Link | Maps To |
|-----------|---------|
| `axbi://dashboard/{id}` | `/ax-bi/dashboard/{id}/` |
| `axbi://chart/{id}` | `/explore/?slice_id={id}` |
| `axbi://explore` | `/explore/` |
| `axbi://sqllab` | `/sqllab/` |
| `axbi://home` | `/ax-bi/welcome/` |

### Content Security Policy

The CSP in `tauri.conf.json` is permissive for local development. For production, restrict origins to your actual server domain.

## Project Structure

```
ax-bi-desktop/
├── (CI) ../../.github/workflows/ax-bi-desktop.yml  # PR checks
├── src/                          # TypeScript bridge code
│   └── api.ts                   # Tauri command bindings
├── src-tauri/                   # Rust backend
│   ├── src/
│   │   ├── main.rs             # App entry, plugin setup
│   │   ├── commands/mod.rs     # Tauri invoke handlers
│   │   ├── deep_link.rs        # axbi:// URL parsing + routing
│   │   └── tray.rs             # System tray setup
│   ├── icons/                   # App icons (512x512 PNG)
│   ├── Cargo.toml              # Rust dependencies
│   └── tauri.conf.json         # Window config, CSP, deep links
├── package.json                 # Node.js deps + npm scripts
└── README.md

Phase 1 frontend components (in ax-bi-frontend/):
├── src/components/
│   ├── CommandPalette/          # Modal + context provider
│   ├── KeyboardShortcuts/       # Shortcut registry + provider
│   └── DesktopIntegration/      # Wires everything into the app
├── src/hooks/
│   ├── useKeyboardShortcuts.ts  # Register shortcuts
│   ├── useServiceWorker.ts      # SW lifecycle
│   └── useDefaultCommands.ts    # Nav + action commands
└── src/service-worker.ts        # Caching strategies
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `⌘K` / `Ctrl+K` | Open command palette |
| `?` | Show shortcut help (when available) |

The command palette includes navigation commands (Dashboards, Charts, SQL Lab, etc.) and action commands (New Dashboard, New Chart, etc.) with fuzzy search.

## Security Considerations

- Local runtime commands are available only from the bundled launcher origin
- Hosted or local AX BI web content does not receive local runtime privileges
- No database credentials are stored in the desktop client
- Authentication uses the same SSO/OIDC flows as the web app
- Production builds are signed (macOS notarization, Windows Authenticode)
- Updates ship via Homebrew / new installers / winget when published (no in-app auto-updater yet)
- CSP must be tightened for production deployments

## Troubleshooting

### macOS: App won't open
If you see "AX BI is damaged and can't be opened":
```bash
xattr -cr "/Applications/AX BI.app"
```

### Rust compilation errors
Ensure your Rust toolchain is up to date:
```bash
rustup update stable
```

### AX BI not loading in Tauri window
Verify the configured AX BI server is running:
```bash
curl -f http://127.0.0.1:31423/health
```

### Windows: WebView2 not found
WebView2 is included with Windows 10/11, or download from [Microsoft](https://developer.microsoft.com/en-us/microsoft-edge/webview2/).

### Linux desktop shell
Linux is not a published desktop release target. Server deployments use Docker
Compose or Helm. WebKit prerequisites only apply if you build the Tauri shell
from source on Linux for development.

## License

Apache License 2.0 — See [LICENSE](../LICENSE) for details.
