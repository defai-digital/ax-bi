#!/usr/bin/env node
/**
 * Sign (or verify) release artifacts with minisign.
 *
 * Local defaults (macOS):
 *   ~/signkey/ax.minisign.key (may be a symlink to ax.sec)
 *   ~/signkey/ax.pub
 *   Keychain service/account: ax-minisign/ax-release (optional passphrase)
 *
 * CI:
 *   Decode AX_BI_MINISIGN_SECRET_KEY_B64 / PUBLIC_KEY into --key-dir and set
 *   MINISIGN_PASSWORD or AX_BI_MINISIGN_PASSWORD.
 *
 * Usage:
 *   node scripts/release/minisign-artifacts.mjs [--key-dir <path>] [--verify-only] [--force] <file...>
 */

import { execFileSync, spawnSync } from 'node:child_process'
import crypto from 'node:crypto'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const args = new Map()
const files = []
const booleanArgs = new Set(['verify-only', 'force'])

for (let index = 2; index < process.argv.length; index += 1) {
  const arg = process.argv[index]

  if (arg.startsWith('--')) {
    const name = arg.slice(2)
    if (booleanArgs.has(name)) {
      args.set(name, 'true')
      continue
    }
    const value = process.argv[index + 1]
    if (value === undefined || value.startsWith('--')) {
      args.set(name, 'true')
    } else {
      args.set(name, value)
      index += 1
    }
  } else {
    files.push(arg)
  }
}

function usage() {
  console.error(
    'usage: node scripts/release/minisign-artifacts.mjs [--key-dir <path>] [--secret-key <path>] [--public-key <path>] [--pinned-public-key <path>] [--password-keychain-service <name>] [--password-keychain-account <name>] [--verify-only] [--force] <file...>',
  )
}

function fail(message) {
  console.error(`minisign error: ${message}`)
  process.exit(1)
}

function expandHome(value) {
  if (!value) {
    return value
  }
  if (value === '~') {
    return os.homedir()
  }
  if (value.startsWith('~/')) {
    return path.join(os.homedir(), value.slice(2))
  }
  return value
}

if (files.length === 0) {
  usage()
  process.exit(2)
}

const verifyOnly = args.get('verify-only') === 'true'
const force = args.get('force') === 'true'

function resolvePath(value, fallback) {
  const raw = expandHome(value ?? fallback)
  if (path.isAbsolute(raw)) {
    return raw
  }
  // Prefer cwd so CI can pass `signkey` from the monorepo root.
  return path.resolve(process.cwd(), raw)
}

const keyDir = resolvePath(args.get('key-dir'), path.join(os.homedir(), 'signkey'))
const secretKey = resolvePath(
  args.get('secret-key'),
  path.join(keyDir, 'ax.minisign.key'),
)
const publicKey = resolvePath(
  args.get('public-key'),
  path.join(keyDir, 'ax.pub'),
)
const pinnedPublicKey = resolvePath(
  args.get('pinned-public-key'),
  fileURLToPath(new URL('../../docs/ax-bi.minisign.pub', import.meta.url)),
)
const keychainService = args.get('password-keychain-service') ?? 'ax-minisign'
const keychainAccount = args.get('password-keychain-account') ?? 'ax-release'

if (spawnSync('minisign', ['-v'], { stdio: 'ignore' }).error) {
  fail('minisign is required (brew install minisign)')
}

if (!fs.existsSync(publicKey)) {
  fail(`public key not found: ${publicKey}`)
}

if (!fs.existsSync(pinnedPublicKey)) {
  fail(`pinned public key not found: ${pinnedPublicKey}`)
}

if (!verifyOnly && !fs.existsSync(secretKey)) {
  fail(`secret key not found: ${secretKey}`)
}

if (!verifyOnly && process.platform !== 'win32') {
  const secretMode = fs.statSync(secretKey).mode & 0o777
  const keyDirectoryMode = fs.statSync(path.dirname(secretKey)).mode & 0o777
  if ((secretMode & 0o077) !== 0) {
    fail(`secret key must not be group/world accessible: ${secretKey}`)
  }
  if ((keyDirectoryMode & 0o077) !== 0) {
    fail(`secret key directory must not be group/world accessible: ${path.dirname(secretKey)}`)
  }
}

function publicKeyMaterial(file) {
  return fs
    .readFileSync(file, 'utf8')
    .split(/\r?\n/u)
    .find(line => line.startsWith('RW'))
}

const selectedPublicKey = publicKeyMaterial(publicKey)
const expectedPublicKey = publicKeyMaterial(pinnedPublicKey)
if (!selectedPublicKey || !expectedPublicKey) {
  fail('selected or pinned minisign public key is malformed')
}
if (selectedPublicKey !== expectedPublicKey) {
  fail(`public key does not match pinned release key: ${pinnedPublicKey}`)
}

let password
if (!verifyOnly) {
  password =
    process.env.MINISIGN_PASSWORD ||
    process.env.AX_BI_MINISIGN_PASSWORD ||
    undefined

  if (!password && process.platform === 'darwin') {
    const result = spawnSync(
      'security',
      [
        'find-generic-password',
        '-s',
        keychainService,
        '-a',
        keychainAccount,
        '-w',
      ],
      { encoding: 'utf8' },
    )
    if (result.status === 0) {
      password = result.stdout.trim()
    }
  }
}

for (const file of files) {
  const artifactPath = path.isAbsolute(file)
    ? file
    : path.resolve(process.cwd(), file)
  const signaturePath = `${artifactPath}.minisig`

  if (!fs.existsSync(artifactPath)) {
    fail(`artifact not found: ${artifactPath}`)
  }

  if (!verifyOnly) {
    if (fs.existsSync(signaturePath) && !force) {
      fail(`signature already exists: ${signaturePath}. Pass --force to overwrite.`)
    }

    const signArgs = ['-S', '-s', secretKey, '-m', artifactPath, '-x', signaturePath]
    const digest = crypto
      .createHash('sha256')
      .update(fs.readFileSync(artifactPath))
      .digest('hex')
    const signedAt = new Date().toISOString().replace(/\.\d{3}Z$/u, 'Z')
    const trustedComment = `AX BI release ${path.basename(artifactPath)} sha256=${digest} signed=${signedAt}`
    signArgs.push('-t', trustedComment)

    execFileSync('minisign', signArgs, {
      stdio: password ? ['pipe', 'inherit', 'inherit'] : 'inherit',
      input: password ? `${password}\n` : undefined,
      env: process.env,
    })
  }

  execFileSync('minisign', ['-Vm', artifactPath, '-p', publicKey, '-x', signaturePath], {
    stdio: 'inherit',
    env: process.env,
  })
}

console.log(`minisign ok: ${files.length} artifact(s)`)
