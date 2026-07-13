#!/usr/bin/env node
/**
 * Normalize Tauri bundle filenames for GitHub Releases / Homebrew.
 *
 * Tauri emits names with spaces (e.g. "AX BI_0.1.0_aarch64.dmg").
 * Release assets use dots: AX.BI_0.1.0_aarch64.dmg (Studio pattern).
 *
 * Usage:
 *   node scripts/release/rename-release-assets.mjs --version 0.1.0 --bundle-dir <path> --out-dir <path>
 */

import fs from 'node:fs'
import path from 'node:path'

const args = new Map()
for (let index = 2; index < process.argv.length; index += 1) {
  const key = process.argv[index]
  const value = process.argv[index + 1]
  if (!key.startsWith('--') || value === undefined || value.startsWith('--')) {
    console.error(
      'usage: node scripts/release/rename-release-assets.mjs --version <version> --bundle-dir <path> --out-dir <path>',
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
const bundleDir = path.resolve(required('bundle-dir'))
const outDir = path.resolve(required('out-dir'))

fs.mkdirSync(outDir, { recursive: true })

const mappings = []

function walk(dir) {
  if (!fs.existsSync(dir)) {
    return
  }
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      walk(full)
      continue
    }
    const lower = entry.name.toLowerCase()
    if (
      lower.endsWith('.dmg') ||
      lower.endsWith('.msi') ||
      lower.endsWith('.exe') ||
      lower.endsWith('.appimage') ||
      lower.endsWith('.deb')
    ) {
      mappings.push(full)
    }
  }
}

walk(bundleDir)

if (mappings.length === 0) {
  console.error(`no release artifacts found under ${bundleDir}`)
  process.exit(1)
}

const copied = []
for (const source of mappings) {
  const base = path.basename(source)
  // "AX BI_0.1.0_aarch64.dmg" → "AX.BI_0.1.0_aarch64.dmg"
  const renamed = base.replace(/^AX BI/i, 'AX.BI').replace(/ /g, '.')
  const dest = path.join(outDir, renamed)
  fs.copyFileSync(source, dest)
  copied.push(dest)
  console.log(`${base} -> ${renamed}`)
}

// macOS: also zip the .app for optional direct download / recovery.
const appCandidates = [
  path.join(bundleDir, 'macos', 'AX BI.app'),
  path.join(bundleDir, 'AX BI.app'),
]
for (const appPath of appCandidates) {
  if (fs.existsSync(appPath)) {
    const zipName = `AX.BI_${version}_aarch64.app.zip`
    const zipPath = path.join(outDir, zipName)
    // Caller on macOS should prefer ditto/zip; we only note the path.
    fs.writeFileSync(
      path.join(outDir, 'app-bundle.path'),
      `${appPath}\n${zipPath}\n`,
    )
    console.log(`app bundle noted: ${appPath}`)
    break
  }
}

console.log(`prepared ${copied.length} artifact(s) in ${outDir}`)
