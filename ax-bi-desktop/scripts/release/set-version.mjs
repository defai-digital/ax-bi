#!/usr/bin/env node
/**
 * Sync desktop package versions for a release.
 *
 * Usage:
 *   node scripts/release/set-version.mjs --version 0.1.0
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const desktopRoot = path.resolve(scriptDir, '..', '..')

const args = new Map()
for (let index = 2; index < process.argv.length; index += 1) {
  const key = process.argv[index]
  const value = process.argv[index + 1]
  if (!key.startsWith('--') || value === undefined || value.startsWith('--')) {
    console.error('usage: node scripts/release/set-version.mjs --version <version>')
    process.exit(2)
  }
  args.set(key.slice(2), value)
  index += 1
}

const version = args.get('version')
if (!version || !/^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$/.test(version)) {
  console.error(`version must look like 0.1.0, got: ${version ?? '(missing)'}`)
  process.exit(2)
}

const tauriConfPath = path.join(desktopRoot, 'src-tauri', 'tauri.conf.json')
const cargoTomlPath = path.join(desktopRoot, 'src-tauri', 'Cargo.toml')
const packageJsonPath = path.join(desktopRoot, 'package.json')

const tauriConf = JSON.parse(fs.readFileSync(tauriConfPath, 'utf8'))
tauriConf.version = version
fs.writeFileSync(tauriConfPath, `${JSON.stringify(tauriConf, null, 2)}\n`)

let cargoToml = fs.readFileSync(cargoTomlPath, 'utf8')
cargoToml = cargoToml.replace(/^version = "[^"]+"/m, `version = "${version}"`)
fs.writeFileSync(cargoTomlPath, cargoToml)

const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'))
packageJson.version = version
fs.writeFileSync(packageJsonPath, `${JSON.stringify(packageJson, null, 2)}\n`)

console.log(`set desktop version to ${version}`)
