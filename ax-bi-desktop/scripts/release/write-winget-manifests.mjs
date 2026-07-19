#!/usr/bin/env node
/**
 * Write winget multi-file manifests for DEFAI.AXBI (NSIS + MSI).
 *
 * Mirrors write-homebrew-cask.mjs: deterministic output from version + hashes.
 * Prefer --artifact-dir so SHA-256 is computed from real files.
 *
 * Usage:
 *   node scripts/release/write-winget-manifests.mjs \
 *     --version 0.1.0 \
 *     --artifact-dir /path/to/assets \
 *     --out-dir /path/to/out
 *
 *   node scripts/release/write-winget-manifests.mjs \
 *     --version 0.1.0 \
 *     --nsis-sha256 <64-hex> \
 *     --msi-sha256 <64-hex> \
 *     --nsis-name AX.BI_0.1.0_x64-setup.exe \
 *     --msi-name AX.BI_0.1.0_x64_en-US.msi \
 *     --out-dir /path/to/out
 *
 * Options:
 *   --tag <tag>              Default: ax-bi-desktop-v{version}
 *   --repo <owner/name>      Default: defai-digital/ax-bi
 *   --release-date YYYY-MM-DD  Optional Installer ReleaseDate
 *   --include-msi true|false Default: true when MSI is available
 */

import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'

const PACKAGE_IDENTIFIER = 'DEFAI.AXBI'
const MANIFEST_VERSION = '1.6.0'
const USAGE = `usage: node scripts/release/write-winget-manifests.mjs \\
  --version <version> --out-dir <path> \\
  (--artifact-dir <path> | --nsis-sha256 <hex> --msi-sha256 <hex> --nsis-name <file> --msi-name <file>) \\
  [--tag <tag>] [--repo <owner/name>] [--release-date YYYY-MM-DD] [--include-msi true|false]`

const args = new Map()
for (let index = 2; index < process.argv.length; index += 1) {
  const key = process.argv[index]
  const value = process.argv[index + 1]
  if (!key.startsWith('--') || value === undefined || value.startsWith('--')) {
    console.error(USAGE)
    process.exit(2)
  }
  args.set(key.slice(2), value)
  index += 1
}

function required(name) {
  const value = args.get(name)
  if (!value) {
    console.error(`missing required argument: --${name}`)
    console.error(USAGE)
    process.exit(2)
  }
  return value
}

function parseBool(name, defaultValue) {
  const raw = args.get(name)
  if (raw === undefined) {
    return defaultValue
  }
  if (raw === 'true' || raw === '1') {
    return true
  }
  if (raw === 'false' || raw === '0') {
    return false
  }
  console.error(`--${name} must be true or false, got: ${raw}`)
  process.exit(2)
}

function isSha256(value) {
  return /^[0-9a-f]{64}$/i.test(value)
}

function sha256File(filePath) {
  const hash = crypto.createHash('sha256')
  hash.update(fs.readFileSync(filePath))
  return hash.digest('hex').toUpperCase()
}

function findArtifact(dir, predicate) {
  if (!fs.existsSync(dir)) {
    return null
  }
  const names = fs.readdirSync(dir).filter(name => !name.endsWith('.minisig'))
  const matches = names.filter(predicate).sort()
  if (matches.length === 0) {
    return null
  }
  return matches[0]
}

const version = required('version')
const outDir = path.resolve(required('out-dir'))
const tag = args.get('tag') ?? `ax-bi-desktop-v${version}`
const repo = args.get('repo') ?? 'defai-digital/ax-bi'
const releaseDate = args.get('release-date')
const includeMsi = parseBool('include-msi', true)

if (!/^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$/.test(version)) {
  console.error(`version must look like 0.1.0, got: ${version}`)
  process.exit(2)
}

if (releaseDate !== undefined && !/^\d{4}-\d{2}-\d{2}$/.test(releaseDate)) {
  console.error(`release-date must be YYYY-MM-DD, got: ${releaseDate}`)
  process.exit(2)
}

let nsisName = args.get('nsis-name')
let msiName = args.get('msi-name')
let nsisSha256 = args.get('nsis-sha256')
let msiSha256 = args.get('msi-sha256')

const artifactDir = args.get('artifact-dir')
if (artifactDir) {
  const resolved = path.resolve(artifactDir)
  const foundNsis =
    findArtifact(
      resolved,
      name =>
        name.startsWith(`AX.BI_${version}_`) &&
        name.endsWith('-setup.exe') &&
        name.includes('x64'),
    ) ??
    findArtifact(
      resolved,
      name => name.endsWith('-setup.exe') && name.includes('x64'),
    )
  const foundMsi =
    findArtifact(
      resolved,
      name =>
        name.startsWith(`AX.BI_${version}_`) &&
        name.endsWith('.msi') &&
        name.includes('x64'),
    ) ??
    findArtifact(
      resolved,
      name => name.endsWith('.msi') && name.includes('x64'),
    )

  if (!foundNsis) {
    console.error(`no x64 NSIS setup.exe found under ${resolved}`)
    process.exit(1)
  }
  nsisName = foundNsis
  nsisSha256 = sha256File(path.join(resolved, foundNsis))

  if (includeMsi) {
    if (!foundMsi) {
      console.error(
        `no x64 MSI found under ${resolved} (pass --include-msi false to skip)`,
      )
      process.exit(1)
    }
    msiName = foundMsi
    msiSha256 = sha256File(path.join(resolved, foundMsi))
  }
} else {
  nsisName = required('nsis-name')
  nsisSha256 = required('nsis-sha256')
  if (includeMsi) {
    msiName = required('msi-name')
    msiSha256 = required('msi-sha256')
  }
}

if (!nsisName || !isSha256(nsisSha256)) {
  console.error('NSIS name and 64-char hex sha256 are required')
  process.exit(2)
}
nsisSha256 = nsisSha256.toUpperCase()

if (includeMsi) {
  if (!msiName || !isSha256(msiSha256)) {
    console.error(
      'MSI name and 64-char hex sha256 are required when include-msi is true',
    )
    process.exit(2)
  }
  msiSha256 = msiSha256.toUpperCase()
}

function installerUrl(fileName) {
  return `https://github.com/${repo}/releases/download/${tag}/${fileName}`
}

const releaseDateLine = releaseDate ? `ReleaseDate: ${releaseDate}\n` : ''

const nsisBlock = `  - Architecture: x64
    InstallerType: nullsoft
    Scope: user
    InstallerUrl: ${installerUrl(nsisName)}
    InstallerSha256: ${nsisSha256}
    InstallerSwitches:
      Silent: /S
      SilentWithProgress: /S
`

const msiBlock = includeMsi
  ? `  - Architecture: x64
    InstallerType: wix
    Scope: machine
    InstallerUrl: ${installerUrl(msiName)}
    InstallerSha256: ${msiSha256}
    InstallerSwitches:
      Silent: /qn /norestart
      SilentWithProgress: /qb /norestart
`
  : ''

const versionYaml = `PackageIdentifier: ${PACKAGE_IDENTIFIER}
PackageVersion: ${version}
DefaultLocale: en-US
ManifestType: version
ManifestVersion: ${MANIFEST_VERSION}
`

const installerYaml = `PackageIdentifier: ${PACKAGE_IDENTIFIER}
PackageVersion: ${version}
Platform:
  - Windows.Desktop
MinimumOSVersion: 10.0.17763.0
InstallModes:
  - interactive
  - silent
  - silentWithProgress
UpgradeBehavior: install
Protocols:
  - axbi
${releaseDateLine}Installers:
${nsisBlock}${msiBlock}ManifestType: installer
ManifestVersion: ${MANIFEST_VERSION}
`

const localeYaml = `PackageIdentifier: ${PACKAGE_IDENTIFIER}
PackageVersion: ${version}
PackageLocale: en-US
Publisher: DEFAI Private Limited
PublisherUrl: https://github.com/defai-digital
PublisherSupportUrl: https://github.com/defai-digital/ax-bi/issues
Author: DEFAI Private Limited
PackageName: AX BI
PackageUrl: https://github.com/defai-digital/ax-bi
License: Apache-2.0
LicenseUrl: https://github.com/defai-digital/ax-bi/blob/main/LICENSE.txt
Copyright: Copyright (c) DEFAI Private Limited
ShortDescription: Desktop client and local runtime launcher for AX BI
Description: >-
  AX BI Desktop is a thin native shell for the AX BI analytics platform.
  Connect to a hosted AX BI server, or run a local Docker-backed instance
  managed by the app (Docker Desktop required for Run locally).
Moniker: ax-bi
Tags:
  - analytics
  - bi
  - dashboard
  - mcp
  - genai
ReleaseNotesUrl: https://github.com/defai-digital/ax-bi/releases/tag/${tag}
ManifestType: defaultLocale
ManifestVersion: ${MANIFEST_VERSION}
`

const packageDir = path.join(
  outDir,
  'manifests',
  'd',
  'DEFAI',
  'AXBI',
  version,
)
fs.mkdirSync(packageDir, { recursive: true })

const files = {
  [`${PACKAGE_IDENTIFIER}.yaml`]: versionYaml,
  [`${PACKAGE_IDENTIFIER}.installer.yaml`]: installerYaml,
  [`${PACKAGE_IDENTIFIER}.locale.en-US.yaml`]: localeYaml,
}

for (const [name, body] of Object.entries(files)) {
  const target = path.join(packageDir, name)
  fs.writeFileSync(target, body)
  console.log(`wrote ${target}`)
}

console.log(
  `winget manifests for ${PACKAGE_IDENTIFIER} ${version} → ${packageDir}`,
)
