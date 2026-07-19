import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import {
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { afterEach, test } from 'node:test'
import crypto from 'node:crypto'

const desktopRoot = path.resolve(import.meta.dirname, '..', '..')
const repositoryRoot = path.resolve(desktopRoot, '..')
const writer = path.join(
  desktopRoot,
  'scripts',
  'release',
  'write-winget-manifests.mjs',
)
const workflow = path.join(
  repositoryRoot,
  '.github',
  'workflows',
  'ax-bi-desktop-release.yml',
)
const temporaryDirectories = []

afterEach(() => {
  for (const directory of temporaryDirectories.splice(0)) {
    rmSync(directory, { recursive: true, force: true })
  }
})

function tempDir(prefix) {
  const root = mkdtempSync(path.join(os.tmpdir(), prefix))
  temporaryDirectories.push(root)
  return root
}

function runWriter(args, expectStatus = 0) {
  const result = spawnSync(process.execPath, [writer, ...args], {
    cwd: desktopRoot,
    encoding: 'utf8',
  })
  assert.equal(
    result.status,
    expectStatus,
    `stdout:\n${result.stdout}\nstderr:\n${result.stderr}`,
  )
  return result
}

function sha256(content) {
  return crypto.createHash('sha256').update(content).digest('hex').toUpperCase()
}

test('write-winget-manifests generates multi-file manifests from artifact-dir', () => {
  const artifacts = tempDir('ax-bi-winget-art-')
  const out = tempDir('ax-bi-winget-out-')
  const nsisBody = Buffer.from('nsis-installer-bytes')
  const msiBody = Buffer.from('msi-installer-bytes')
  const nsisName = 'AX.BI_0.1.0_x64-setup.exe'
  const msiName = 'AX.BI_0.1.0_x64_en-US.msi'
  writeFileSync(path.join(artifacts, nsisName), nsisBody)
  writeFileSync(path.join(artifacts, msiName), msiBody)
  writeFileSync(path.join(artifacts, `${nsisName}.minisig`), 'sig')

  runWriter([
    '--version',
    '0.1.0',
    '--tag',
    'ax-bi-desktop-v0.1.0',
    '--artifact-dir',
    artifacts,
    '--out-dir',
    out,
    '--release-date',
    '2026-07-19',
  ])

  const packageDir = path.join(out, 'manifests', 'd', 'DEFAI', 'AXBI', '0.1.0')
  const versionYaml = readFileSync(path.join(packageDir, 'DEFAI.AXBI.yaml'), 'utf8')
  const installerYaml = readFileSync(
    path.join(packageDir, 'DEFAI.AXBI.installer.yaml'),
    'utf8',
  )
  const localeYaml = readFileSync(
    path.join(packageDir, 'DEFAI.AXBI.locale.en-US.yaml'),
    'utf8',
  )

  assert.match(versionYaml, /PackageIdentifier: DEFAI\.AXBI/)
  assert.match(versionYaml, /PackageVersion: 0\.1\.0/)
  assert.match(versionYaml, /ManifestType: version/)

  assert.match(installerYaml, /InstallerType: nullsoft/)
  assert.match(installerYaml, /InstallerType: wix/)
  assert.match(installerYaml, /Scope: user/)
  assert.match(installerYaml, /Scope: machine/)
  assert.match(installerYaml, /ReleaseDate: 2026-07-19/)
  assert.match(
    installerYaml,
    new RegExp(
      `InstallerUrl: https://github.com/defai-digital/ax-bi/releases/download/ax-bi-desktop-v0\\.1\\.0/${nsisName.replace(/\./g, '\\.')}`,
    ),
  )
  assert.match(installerYaml, new RegExp(`InstallerSha256: ${sha256(nsisBody)}`))
  assert.match(installerYaml, new RegExp(`InstallerSha256: ${sha256(msiBody)}`))
  assert.ok(!installerYaml.includes('.minisig'))

  assert.match(localeYaml, /Publisher: DEFAI Private Limited/)
  assert.match(localeYaml, /Moniker: ax-bi/)
  assert.match(localeYaml, /PackageLocale: en-US/)
  assert.match(localeYaml, /ManifestType: defaultLocale/)
})

test('write-winget-manifests accepts explicit hashes and can omit MSI', () => {
  const out = tempDir('ax-bi-winget-hash-')
  const nsisSha = 'a'.repeat(64)
  runWriter([
    '--version',
    '2.1.1',
    '--out-dir',
    out,
    '--nsis-name',
    'AX.BI_2.1.1_x64-setup.exe',
    '--nsis-sha256',
    nsisSha,
    '--include-msi',
    'false',
  ])

  const installerYaml = readFileSync(
    path.join(out, 'manifests', 'd', 'DEFAI', 'AXBI', '2.1.1', 'DEFAI.AXBI.installer.yaml'),
    'utf8',
  )
  assert.match(installerYaml, new RegExp(`InstallerSha256: ${'A'.repeat(64)}`))
  assert.ok(!installerYaml.includes('InstallerType: wix'))
  assert.match(installerYaml, /InstallerType: nullsoft/)
})

test('write-winget-manifests rejects invalid version and short hash', () => {
  const out = tempDir('ax-bi-winget-bad-')
  runWriter(
    [
      '--version',
      'v0.1.0',
      '--out-dir',
      out,
      '--nsis-name',
      'x.exe',
      '--nsis-sha256',
      'a'.repeat(64),
      '--include-msi',
      'false',
    ],
    2,
  )
  runWriter(
    [
      '--version',
      '0.1.0',
      '--out-dir',
      out,
      '--nsis-name',
      'x.exe',
      '--nsis-sha256',
      'deadbeef',
      '--include-msi',
      'false',
    ],
    2,
  )
})

test('write-winget-manifests fails when artifact-dir lacks NSIS', () => {
  const artifacts = tempDir('ax-bi-winget-empty-')
  const out = tempDir('ax-bi-winget-empty-out-')
  mkdirSync(artifacts, { recursive: true })
  writeFileSync(path.join(artifacts, 'readme.txt'), 'no installers')
  runWriter(
    ['--version', '0.1.0', '--artifact-dir', artifacts, '--out-dir', out],
    1,
  )
})

test('release workflow prepares winget manifests after publish with minisign gate', () => {
  const text = readFileSync(workflow, 'utf8')
  assert.match(text, /skip_winget:/)
  assert.ok(text.includes('prepare-winget-manifests:'))
  assert.ok(text.includes('write-winget-manifests.mjs'))
  assert.ok(
    text.includes('AX.BI_${VERSION}_winget-manifests.zip') ||
      text.includes('winget-manifests.zip'),
  )

  const wingetJob =
    text.match(/  prepare-winget-manifests:[\s\S]*?(?=\n  [a-z]|\n*$)/u)?.[0] ??
    ''
  assert.ok(wingetJob.includes('needs: [resolve-version, publish-release]'))
  assert.ok(wingetJob.includes('minisign -V'))
  assert.ok(wingetJob.includes('write-winget-manifests.mjs'))
  const minisignAt = wingetJob.indexOf('minisign -V')
  const writeAt = wingetJob.indexOf('write-winget-manifests.mjs')
  assert.ok(minisignAt >= 0 && writeAt >= 0 && minisignAt < writeAt)
})
