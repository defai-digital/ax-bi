# AX BI Desktop Client

A thin desktop client for the AX BI data visualization and analytics platform, built with [Tauri v2](https://tauri.app/).

## Overview

AX BI Desktop delivers a native desktop experience for the AX BI web application through two complementary layers:

### Phase 1 — PWA + Desktop-Grade UX (in the web app)

These features live in `ax-bi-frontend/` and work in both the browser and the Tauri shell:

- **Command palette** — `⌘K` / `Ctrl+K` fuzzy-search across all navigation and actions
- **Global keyboard shortcuts** — OS-aware shortcut registry with help overlay
- **Service worker** — Offline-capable caching (stale-while-revalidate for assets, network-first for API)
- **PWA installability** — Install the web app directly from the browser (Chrome, Edge)

### Phase 2 — Tauri Desktop Shell

These features live in `superset-desktop/` and require the native app:

- **Native window** — Standalone desktop shell for local or hosted AX BI
- **First-run home** — Run a local Docker instance or connect to a remote server (ops controls stay under Advanced)
- **Full-bleed BI** — Once open, the web app fills the window (no extra desktop top bar)
- **Desktop actions in web Settings** — Desktop home / Desktop settings (also ⌘, / ⌘⇧H)
- **Settings drawer** — Local instance, remote connection, theme; runtime logs/deps behind Advanced
- **Deep links** — `axbi://dashboard/{id}`, `axbi://chart/{id}` open directly in the app
- **System tray** — Quick access to dashboards and SQL Lab (infrastructure in place)
- **Cross-platform builds** — macOS, Windows, and Linux via GitHub Actions

## Architecture

The desktop client is a **thin shell** with a bundled product launcher. It does
**not** bundle the Python backend, database drivers, or any server-side
components. The home screen offers two primary paths: run a local Docker-based
instance (app-managed Colima/Compose), or connect to a hosted AX BI server.
Colima/Docker status, logs, and prepare/stop/update controls live under
**Settings → Advanced runtime**.

## Recommended User Install

The intended macOS user path is a Homebrew cask that installs AX BI Desktop and
the local runtime prerequisites:

```bash
brew install --cask defai-digital/ax-bi/ax-bi
```

After installation, AX BI Desktop should guide the user to either connect to an
existing AX BI server or start a local AX BI runtime. The local runtime manager
uses Colima and Docker Compose behind the Tauri app so users do not need to
clone this repository, edit `.env` files, or run Docker commands manually.

See [LOCAL_RUNTIME.md](LOCAL_RUNTIME.md) for the runtime architecture, command
contract, Homebrew cask shape, and security boundary.

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
│  │  │  Service Worker · PWA Install · Keyboard Shortcuts   │  │  │
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
cd superset-desktop
npm install           # First time only
npm run dev           # Builds Rust + launches native window
```

The first `cargo` build can take several minutes. When the window opens:

1. **Run locally** — prepares/starts the app-managed Colima + Docker stack, or
2. **Connect to server** — paste a hosted AX BI URL

When local AX BI is healthy, the shell opens the web app full-bleed and shows a
**Local admin login** toast (also under Settings → Advanced → Credentials).

Default local login:

- username: `admin`
- password: `admin`

### 2. Optional local backend

```bash
superset run -p 8088 --with-threads --reload --debugger
```

The launcher can also start the app-managed Docker/Colima runtime.

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
superset-desktop/
├── .github/workflows/build.yml   # Cross-platform CI/CD
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
│   ├── PWAInstallPrompt/        # Install banner
│   └── DesktopIntegration/      # Wires everything into the app
├── src/hooks/
│   ├── useKeyboardShortcuts.ts  # Register shortcuts
│   ├── useServiceWorker.ts      # SW lifecycle
│   ├── usePWAInstall.ts         # Install state
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
- Production builds should be signed (macOS notarization, Windows code signing)
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
curl -f http://127.0.0.1:8088/health
```

### Windows: WebView2 not found
WebView2 is included with Windows 10/11, or download from [Microsoft](https://developer.microsoft.com/en-us/microsoft-edge/webview2/).

### Linux: Missing dependencies
```bash
sudo apt-get install libwebkit2gtk-4.1-dev libappindicator3-dev
```

## License

Apache License 2.0 — See [LICENSE](../LICENSE) for details.
# AX BI Desktop Client

A thin desktop client for the AX BI data visualization and analytics platform, built with [Tauri](https://tauri.app/).

## Overview

AX BI Desktop provides native desktop integration for the AX BI web application, including:

- **System tray** - Quick access to dashboards and SQL Lab from your system tray
- **Deep links** - Open `axbi://dashboard/123` or `axbi://chart/456` directly in the app
- **Native notifications** - Receive desktop notifications for alerts and updates
- **File associations** - Open CSV, Excel, and Parquet files directly in AX BI
- **Auto-update** - Automatic updates for the latest features and security patches

## Architecture

The desktop client is a thin shell that loads the AX BI web application. It does **not** bundle the Python backend, database drivers, or any server-side components. The web app remains the source of truth.

```
┌─────────────────────────────────────────────────────────────┐
│                    AX BI Desktop Client                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 Tauri WebView                        │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │          AX BI Web Application               │   │   │
│  │  │  (Loaded from https://your-axbi-instance)   │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  Native Features:                                           │
│  • System Tray      • Deep Links      • Notifications       │
│  • File Handlers    • Auto-Update     • Native Menus        │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

- **Node.js**: 20.x or later
- **Rust**: 1.75 or later (via [rustup](https://rustup.rs/))
- **Platform-specific dependencies**:
  - **macOS**: Xcode Command Line Tools
  - **Windows**: WebView2 (included in Windows 10/11)
  - **Linux**: See [Tauri prerequisites](https://tauri.app/v1/guides/getting-started/prerequisites)

## Development

### Install dependencies

```bash
cd superset-desktop
npm install
```

### Run in development mode

```bash
npm run dev
```

This will start the Tauri app in development mode with hot reload.

### Build for production

```bash
npm run build
```

This will create a macOS bundle:
- **macOS app**: `src-tauri/target/release/bundle/macos/`

## Configuration

### Server URL

The desktop client connects to your AX BI server. Configure the server URL:

1. **Environment variable** (recommended for development):
   ```bash
   export AXBI_SERVER_URL=https://your-axbi-instance.com
   ```

2. **Edit `src-tauri/tauri.conf.json`**:
   ```json
   {
     "app": {
       "windows": [{
         "url": "https://your-axbi-instance.com"
       }]
     }
   }
   ```

### Deep Links

The desktop client registers the `axbi://` URL scheme. Supported deep links:

| Deep Link | Action |
|-----------|--------|
| `axbi://dashboard/{id}` | Open a specific dashboard |
| `axbi://chart/{id}` | Open a specific chart |
| `axbi://explore` | Open the chart builder |
| `axbi://sqllab` | Open SQL Lab |
| `axbi://home` | Open the welcome page |

## Project Structure

```
superset-desktop/
├── .github/workflows/     # CI/CD workflows
├── src/                   # TypeScript frontend code
│   └── api.ts            # Tauri command bindings
├── src-tauri/            # Rust backend
│   ├── src/
│   │   ├── main.rs       # Application entry point
│   │   ├── commands/     # Tauri commands
│   │   ├── deep_link.rs  # Deep link handling
│   │   └── tray.rs       # System tray setup
│   ├── icons/            # App icons
│   ├── Cargo.toml        # Rust dependencies
│   └── tauri.conf.json   # Tauri configuration
├── package.json          # Node.js dependencies
└── README.md
```

## Security Considerations

- The WebView only loads content from trusted, configured origins
- No direct database credentials are stored in the desktop client
- Authentication uses the same SSO/OIDC flows as the web app
- All updates are signed and verified before installation

## Troubleshooting

### macOS: App won't open
If you see "AX BI is damaged and can't be opened":
```bash
xattr -cr "/Applications/AX BI.app"
```

### Windows: WebView2 not found
Ensure WebView2 is installed. It's included with Windows 10/11, or download from [Microsoft](https://developer.microsoft.com/en-us/microsoft-edge/webview2/).

### Linux: Missing dependencies
Install required packages:
```bash
sudo apt-get install libwebkit2gtk-4.1-dev libappindicator3-dev
```

## License

Apache License 2.0 - See [LICENSE](../LICENSE) for details.
