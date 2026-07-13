#!/usr/bin/env node
/**
 * Write Casks/ax-bi.rb for https://github.com/defai-digital/homebrew-ax-bi
 *
 * Usage:
 *   node scripts/release/write-homebrew-cask.mjs \
 *     --version 0.1.0 \
 *     --sha256 <64-hex> \
 *     --out /path/to/homebrew-ax-bi/Casks/ax-bi.rb
 */

import fs from 'node:fs'
import path from 'node:path'

const args = new Map()

for (let index = 2; index < process.argv.length; index += 1) {
  const key = process.argv[index]
  const value = process.argv[index + 1]

  if (!key.startsWith('--') || value === undefined || value.startsWith('--')) {
    console.error(
      'usage: node scripts/release/write-homebrew-cask.mjs --version <version> --sha256 <sha256> --out <path> [--tag <tag>]',
    )
    process.exit(2)
  }

  args.set(key.slice(2), value)
  index += 1
}

function required(name) {
  const value = args.get(name)
  if (!value) {
    console.error(`missing required argument: --${name}`)
    process.exit(2)
  }
  return value
}

const version = required('version')
const sha256 = required('sha256')
const outPath = path.resolve(required('out'))
const tag = args.get('tag') ?? `ax-bi-desktop-v${version}`

if (!/^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$/.test(version)) {
  console.error(`version must look like 0.1.0, got: ${version}`)
  process.exit(2)
}

if (!/^[0-9a-f]{64}$/i.test(sha256)) {
  console.error(`sha256 must be a 64-character hex digest, got: ${sha256}`)
  process.exit(2)
}

// Matches Studio/Code Desktop: arm64 DMG from GitHub Releases + postflight xattr.
// Local runtime deps (Colima/Docker) are installed by Homebrew formulas.
const cask = `cask "ax-bi" do
  version "${version}"
  sha256 "${sha256}"

  url "https://github.com/defai-digital/ax-bi/releases/download/${tag}/AX.BI_#{version}_aarch64.dmg",
      verified: "github.com/defai-digital/ax-bi/"
  name "AX BI"
  desc "Desktop client and local runtime launcher for AX BI"
  homepage "https://github.com/defai-digital/ax-bi"

  depends_on arch: :arm64
  depends_on macos: :monterey
  depends_on formula: "colima"
  depends_on formula: "docker"
  depends_on formula: "docker-compose"

  app "AX BI.app"

  preflight do
    # Clears any pre-existing bundle so upgrades from untracked installs do not
    # hit Homebrew's "already an App" guard.
    app_path = "#{appdir}/AX BI.app"
    FileUtils.rm_r(app_path) if File.exist?(app_path)
  end

  postflight do
    system_command "/usr/bin/xattr",
                   args: ["-cr", "#{appdir}/AX BI.app"]
  end

  zap trash: [
    "~/Library/Application Support/com.axbi.desktop",
    "~/Library/Caches/com.axbi.desktop",
    "~/Library/Logs/com.axbi.desktop",
    "~/Library/Preferences/com.axbi.desktop.plist",
    "~/Library/Saved Application State/com.axbi.desktop.savedState",
  ]
end
`

fs.mkdirSync(path.dirname(outPath), { recursive: true })
fs.writeFileSync(outPath, cask)
console.log(`wrote ${outPath}`)
