import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import {
  chmodSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { afterEach, test } from 'node:test'

const desktopRoot = path.resolve(import.meta.dirname, '..', '..')
const repositoryRoot = path.resolve(desktopRoot, '..')
const signer = path.join(desktopRoot, 'scripts', 'release', 'minisign-artifacts.mjs')
const manualSigner = path.join(repositoryRoot, 'scripts', 'sign.sh')
const workflow = path.join(repositoryRoot, '.github', 'workflows', 'ax-bi-desktop-release.yml')
const sharedPublicKey = [
  'untrusted comment: minisign public key CF42FC69BEEF0EA5',
  'RWSlDu++afxCz01OqhYWhfo8+L8pVbSYXJBEb2zoWBuK0WACIzbGVZRO',
  '',
].join('\n')
const temporaryDirectories = []

afterEach(() => {
  for (const directory of temporaryDirectories.splice(0)) {
    rmSync(directory, { recursive: true, force: true })
  }
})

function executable(file, source) {
  writeFileSync(file, `#!/usr/bin/env node\n${source}`)
  chmodSync(file, 0o755)
}

function fixture() {
  const root = mkdtempSync(path.join(os.tmpdir(), 'ax-bi-release-signing-'))
  temporaryDirectories.push(root)
  const keyDirectory = path.join(root, 'signkey')
  const binDirectory = path.join(root, 'bin')
  const secretKey = path.join(keyDirectory, 'ax.minisign.key')
  const publicKey = path.join(keyDirectory, 'ax.pub')
  const artifact = path.join(root, 'AX.BI_2.0.6_aarch64.dmg')
  const minisignLog = path.join(root, 'minisign.log')
  const securityLog = path.join(root, 'security.log')

  mkdirSync(keyDirectory, { mode: 0o700 })
  mkdirSync(binDirectory)
  writeFileSync(secretKey, 'encrypted test key')
  chmodSync(secretKey, 0o600)
  writeFileSync(publicKey, sharedPublicKey)
  writeFileSync(artifact, 'release artifact')

  executable(
    path.join(binDirectory, 'minisign'),
    `
const fs = require('node:fs')
const args = process.argv.slice(2)
try { fs.readFileSync(0, 'utf8') } catch {}
fs.appendFileSync(process.env.MINISIGN_TEST_LOG, JSON.stringify(args) + '\\n')
if (args.includes('-S')) {
  const signature = args[args.indexOf('-x') + 1]
  fs.writeFileSync(signature, 'test signature')
}
`,
  )
  executable(
    path.join(binDirectory, 'security'),
    `
require('node:fs').appendFileSync(
  process.env.SECURITY_TEST_LOG,
  JSON.stringify(process.argv.slice(2)) + '\\n',
)
process.stdout.write('from-keychain\\n')
`,
  )

  return {
    root,
    keyDirectory,
    binDirectory,
    secretKey,
    publicKey,
    artifact,
    minisignLog,
    securityLog,
  }
}

test('signer pins the shared key, uses the generic Keychain item, and records artifact identity', () => {
  const f = fixture()
  const result = spawnSync(
    process.execPath,
    [signer, '--key-dir', f.keyDirectory, f.artifact],
    {
      cwd: desktopRoot,
      encoding: 'utf8',
      env: {
        ...process.env,
        PATH: `${f.binDirectory}:${process.env.PATH}`,
        MINISIGN_PASSWORD: '',
        MINISIGN_TEST_LOG: f.minisignLog,
        SECURITY_TEST_LOG: f.securityLog,
      },
    },
  )

  assert.equal(result.status, 0, result.stderr)
  const invocations = readFileSync(f.minisignLog, 'utf8')
    .trim()
    .split('\n')
    .map(line => JSON.parse(line))
  const signArgs = invocations.find(args => args.includes('-S'))
  const trustedComment = signArgs[signArgs.indexOf('-t') + 1]
  assert.match(trustedComment, /AX BI release AX\.BI_2\.0\.6_aarch64\.dmg sha256=[0-9a-f]{64} signed=/u)
  assert.ok(invocations.some(args => args.includes('-Vm')))

  const securityArgs = JSON.parse(readFileSync(f.securityLog, 'utf8').trim())
  assert.ok(securityArgs.includes('ax-minisign'))
  assert.ok(securityArgs.includes('ax-release'))
})

test('signer rejects a public key that differs from the committed release pin', () => {
  const f = fixture()
  writeFileSync(f.publicKey, 'untrusted comment: wrong key\nRWS_WRONG_PUBLIC_KEY\n')
  const result = spawnSync(
    process.execPath,
    [signer, '--key-dir', f.keyDirectory, f.artifact],
    {
      cwd: desktopRoot,
      encoding: 'utf8',
      env: {
        ...process.env,
        PATH: `${f.binDirectory}:${process.env.PATH}`,
        MINISIGN_PASSWORD: 'test',
      },
    },
  )

  assert.equal(result.status, 1)
  assert.match(result.stderr, /public key does not match pinned release key/u)
})

test('signer rejects a group-readable secret key', () => {
  const f = fixture()
  chmodSync(f.secretKey, 0o640)
  const result = spawnSync(
    process.execPath,
    [signer, '--key-dir', f.keyDirectory, f.artifact],
    {
      cwd: desktopRoot,
      encoding: 'utf8',
      env: {
        ...process.env,
        PATH: `${f.binDirectory}:${process.env.PATH}`,
        MINISIGN_PASSWORD: 'test',
      },
    },
  )

  assert.equal(result.status, 1)
  assert.match(result.stderr, /secret key must not be group\/world accessible/u)
})

test('manual signer enforces the same pin and trusted-comment contract', () => {
  const f = fixture()
  const result = spawnSync(
    'bash',
    [manualSigner, '--secret-key', f.secretKey, '--public-key', f.publicKey, f.artifact],
    {
      cwd: repositoryRoot,
      encoding: 'utf8',
      env: {
        ...process.env,
        PATH: `${f.binDirectory}:${process.env.PATH}`,
        MINISIGN_PASSWORD: 'test',
        MINISIGN_TEST_LOG: f.minisignLog,
        SECURITY_TEST_LOG: f.securityLog,
      },
    },
  )

  assert.equal(result.status, 0, result.stderr)
  const invocations = readFileSync(f.minisignLog, 'utf8')
    .trim()
    .split('\n')
    .map(line => JSON.parse(line))
  const signArgs = invocations.find(args => args.includes('-S'))
  const trustedComment = signArgs[signArgs.indexOf('-t') + 1]
  assert.match(trustedComment, /AX BI release AX\.BI_2\.0\.6_aarch64\.dmg sha256=[0-9a-f]{64} signed=/u)
})

test('release workflow fails closed before publishing or trusting a Homebrew checksum', () => {
  const text = readFileSync(workflow, 'utf8')
  const homebrewJob = text.match(/  update-homebrew-tap:[\s\S]*$/u)?.[0] ?? ''

  assert.match(text, /secrets\.APPLE_TEAM_ID != ''/u)
  assert.ok(text.includes('verify-macos-release:'))
  assert.ok(text.includes('codesign --verify --deep --strict'))
  assert.ok(text.includes('spctl --assess --type install'))
  assert.ok(text.includes('spctl --assess --type execute'))
  assert.ok(!text.includes('spctl -a -vv -t install "$DMG_PATH" || true'))
  assert.ok(text.includes('verify-minisign:'))
  assert.ok(text.includes('cmp ax-bi-desktop/docs/ax-bi.minisign.pub artifacts/ax-minisign.pub'))
  assert.ok(text.includes('needs: [resolve-version, verify-minisign]'))
  assert.ok(text.includes('Release $TAG is already published; refusing to replace verified assets.'))
  assert.ok(text.includes('Release $TAG is no longer a draft; refusing to publish or mutate it.'))
  assert.ok(!text.includes('already published; later uploads use --clobber'))
  assert.ok(homebrewJob.includes('release.dmg.minisig'))
  assert.ok(homebrewJob.includes('-p ax-bi-desktop/docs/ax-bi.minisign.pub'))
  assert.ok(homebrewJob.indexOf('minisign -V') < homebrewJob.indexOf('DMG_SHA256='))

  const localNotarizer = readFileSync(
    path.join(desktopRoot, 'scripts', 'release', 'notarize-macos.sh'),
    'utf8',
  )
  assert.ok(localNotarizer.includes('spctl --assess --type install'))
})
