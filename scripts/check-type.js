#!/usr/bin/env node

/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

// @ts-check
const { exit } = require("node:process");
const { join, dirname, isAbsolute, normalize, sep } = require("node:path");
const { readdir, stat } = require("node:fs/promises");
const { existsSync } = require("node:fs");
const { chdir, cwd } = require("node:process");
const { createRequire } = require("node:module");
const { execFileSync } = require("node:child_process");

// Increase memory limit for TypeScript compiler
if (!process.env.NODE_OPTIONS?.includes("--max-old-space-size")) {
  process.env.NODE_OPTIONS = `${process.env.NODE_OPTIONS || ""} --max-old-space-size=8192`.trim();
}

const AXBI_ROOT = dirname(__dirname);
const PACKAGE_ARG_REGEX = /^package=/;
const EXCLUDE_DECLARATION_DIR_REGEX = /^excludeDeclarationDir=/;
const DECLARATION_FILE_REGEX = /\.d\.ts$/;
const IGNORE_DEPRECATIONS_OPTION = "--ignoreDeprecations 6.0";

// Configuration for batching and fallback
const MAX_FILES_FOR_TARGETED_CHECK = 20; // Fallback to full check if more files
const BATCH_SIZE = 10; // Process files in batches of this size

void (async () => {
  const args = process.argv.slice(2);

  if (args.includes("--help") || args.includes("-h")) {
    printHelp();
    exit(0);
  }

  const {
    matchedArgs: [packageArg, excludeDeclarationDirArg],
    remainingArgs,
  } = extractArgs(args, [PACKAGE_ARG_REGEX, EXCLUDE_DECLARATION_DIR_REGEX]);

  if (!packageArg) {
    console.error("package is not specified");
    exit(1);
  }

  const packageRootDir = await getPackage(packageArg);
  const changedFiles = filterExistingFiles(
    removePackageSegment(remainingArgs, packageRootDir),
    packageRootDir
  );

  // Filter to only TypeScript files
  const tsFiles = changedFiles.filter(file =>
    /\.(ts|tsx)$/.test(file) && !DECLARATION_FILE_REGEX.test(file)
  );

  console.log(`Type checking ${tsFiles.length} changed TypeScript files...`);

  if (tsFiles.length === 0) {
    console.log("No TypeScript files to check.");
    exit(0);
  }

  // Decide strategy based on number of files
  if (tsFiles.length > MAX_FILES_FOR_TARGETED_CHECK) {
    console.log(`Too many files (${tsFiles.length} > ${MAX_FILES_FOR_TARGETED_CHECK}), running full type check...`);
    await runFullTypeCheck(packageRootDir, excludeDeclarationDirArg);
  } else {
    console.log(`Running targeted type check on ${tsFiles.length} files...`);
    await runTargetedTypeCheck(packageRootDir, tsFiles, excludeDeclarationDirArg);
  }
})();

function printHelp() {
  console.log(`Usage: node scripts/check-type.js package=<dir> [excludeDeclarationDir=<dirs>] [files...]

Run TypeScript checks for changed files in a package.

Arguments:
  package=<dir>                  Package directory to type check.
  excludeDeclarationDir=<dirs>   Comma-separated directories to skip while collecting .d.ts files.
  files...                       Changed files to check; missing files are skipped.

Options:
  -h, --help                     Show this help message and exit.`);
}

/**
 * Run full type check on the entire project
 */
async function runFullTypeCheck(packageRootDir, excludeDeclarationDirArg) {
  const packageRootDirAbsolute = join(AXBI_ROOT, packageRootDir);
  const tsConfig = getTsConfig(packageRootDirAbsolute);
  // Use incremental compilation for better caching
  const command = `--noEmit --allowJs --incremental ${IGNORE_DEPRECATIONS_OPTION} --project ${tsConfig}`;

  await executeTypeCheck(packageRootDirAbsolute, command);
}

/**
 * Run targeted type check on specific files, with batching
 */
async function runTargetedTypeCheck(packageRootDir, tsFiles, excludeDeclarationDirArg) {
  const excludedDeclarationDirs = getExcludedDeclarationDirs(excludeDeclarationDirArg);
  let declarationFiles = await getFilesRecursively(
    join(AXBI_ROOT, packageRootDir),
    DECLARATION_FILE_REGEX,
    excludedDeclarationDirs
  );
  declarationFiles = removePackageSegment(declarationFiles, packageRootDir);

  const packageRootDirAbsolute = join(AXBI_ROOT, packageRootDir);
  const tsConfig = getTsConfig(packageRootDirAbsolute);

  // Process files in batches to avoid command line length limits
  const batches = [];
  for (let i = 0; i < tsFiles.length; i += BATCH_SIZE) {
    batches.push(tsFiles.slice(i, i + BATCH_SIZE));
  }

  let hasErrors = false;

  for (const [batchIndex, batch] of batches.entries()) {
    if (batches.length > 1) {
      console.log(`\nProcessing batch ${batchIndex + 1}/${batches.length} (${batch.length} files)...`);
    }

    const argsStr = batch.join(" ");
    const declarationFilesStr = declarationFiles.join(" ");
    // For targeted checks, keep composite false since we're passing specific files
    const command = `--noEmit --allowJs --composite false ${IGNORE_DEPRECATIONS_OPTION} --project ${tsConfig} ${argsStr} ${declarationFilesStr}`;

    try {
      await executeTypeCheck(
        packageRootDirAbsolute,
        command,
        createDiagnosticFilter(packageRootDirAbsolute, batch)
      );
    } catch (error) {
      hasErrors = true;
      // Continue processing other batches to show all errors
    }
  }

  if (hasErrors) {
    exit(1);
  }
}

/** Normalize a diagnostic file path for comparison across platforms */
function normalizeDiagnosticPath(filePath) {
  return filePath.replace(/\\/g, "/").replace(/^\.\//, "");
}

const ANSI_REGEX = /\x1b\[[0-9;]*m/g;
const DIAGNOSTIC_START_REGEX = /^(.+?\.(?:tsx?|jsx?)):(\d+):\d+ - (?:error|warning) TS\d+/;
const DIFF_HUNK_REGEX = /^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@/;

/**
 * Keep only the diagnostic blocks that belong to the target files.
 *
 * tsc reports errors for the whole program (every file the targets import),
 * so a targeted check would otherwise fail on pre-existing errors in
 * unchanged dependency files.
 */
function filterDiagnostics(stdout, shouldKeepDiagnostic) {
  const lines = stdout.split("\n");
  const kept = [];
  let keepBlock = false;
  let droppedCount = 0;
  let keptCount = 0;

  for (const line of lines) {
    const plain = line.replace(ANSI_REGEX, "");
    const match = plain.match(DIAGNOSTIC_START_REGEX);
    if (match) {
      keepBlock = shouldKeepDiagnostic(match[1], Number(match[2]));
      if (keepBlock) {
        keptCount += 1;
      } else {
        droppedCount += 1;
      }
    } else if (/^(Found \d+ errors?|Errors {2}Files)/.test(plain)) {
      // Drop tsc's own summary; it counts program-wide errors
      keepBlock = false;
      continue;
    }
    if (keepBlock) {
      kept.push(line);
    }
  }

  return { output: kept.join("\n").trim(), keptCount, droppedCount };
}

/**
 * @param {string} packageRootDirAbsolute
 * @param {string[]} tsFiles
 * @returns {Map<string, Set<number>>}
 */
function getChangedLinesByFile(packageRootDirAbsolute, tsFiles) {
  const diffArgs = [
    "diff",
    "--cached",
    "--unified=0",
    "--relative",
    "--",
    ...tsFiles,
  ];
  let diffOutput = "";

  try {
    diffOutput = execFileSync("git", diffArgs, {
      cwd: packageRootDirAbsolute,
      encoding: "utf8",
      maxBuffer: 10 * 1024 * 1024,
    });
  } catch (e) {
    return new Map();
  }

  const changedLinesByFile = new Map();
  let currentFile;

  for (const line of diffOutput.split("\n")) {
    if (line.startsWith("+++ b/")) {
      currentFile = normalizeDiagnosticPath(line.slice("+++ b/".length));
      if (!changedLinesByFile.has(currentFile)) {
        changedLinesByFile.set(currentFile, new Set());
      }
      continue;
    }

    const match = line.match(DIFF_HUNK_REGEX);
    if (!match || !currentFile) {
      continue;
    }

    const start = Number(match[1]);
    const count = match[2] === undefined ? 1 : Number(match[2]);
    const changedLines = changedLinesByFile.get(currentFile);

    for (let offset = 0; offset < count; offset += 1) {
      changedLines.add(start + offset);
    }
  }

  return changedLinesByFile;
}

/**
 * @param {string} packageRootDirAbsolute
 * @param {string[]} tsFiles
 */
function createDiagnosticFilter(packageRootDirAbsolute, tsFiles) {
  const onlyFiles = new Set(tsFiles.map(normalizeDiagnosticPath));
  const changedLinesByFile = getChangedLinesByFile(
    packageRootDirAbsolute,
    tsFiles
  );

  return (filePath, lineNumber) => {
    const normalizedPath = normalizeDiagnosticPath(filePath);
    if (!onlyFiles.has(normalizedPath)) {
      return false;
    }

    const changedLines = changedLinesByFile.get(normalizedPath);
    return changedLines === undefined || changedLines.has(lineNumber);
  };
}

/**
 * Execute the TypeScript type check command.
 *
 * When `shouldKeepDiagnostic` is provided, only diagnostics it accepts fail
 * the check; program-wide diagnostics outside that scope are reported as
 * skipped.
 */
async function executeTypeCheck(
  packageRootDirAbsolute,
  command,
  shouldKeepDiagnostic
) {
  try {
    chdir(packageRootDirAbsolute);
    const tscw = packageRequire("tscw-config");
    const child = await tscw`${command}`;

    if (shouldKeepDiagnostic) {
      const { output, keptCount, droppedCount } = filterDiagnostics(
        child.stdout || "",
        shouldKeepDiagnostic
      );
      if (output) {
        console.log(output);
      }
      if (child.stderr) {
        console.error(child.stderr);
      }
      if (droppedCount > 0) {
        console.log(
          `Ignored ${droppedCount} pre-existing type error(s) in unchanged dependency files.`
        );
      }
      if (keptCount > 0) {
        throw new Error(
          `Type check failed with ${keptCount} error(s) in changed files`
        );
      }
      return;
    }

    if (child.stdout) {
      console.log(child.stdout);
    }

    if (child.stderr) {
      console.error(child.stderr);
    }

    if (child.exitCode !== 0) {
      throw new Error(`Type check failed with exit code ${child.exitCode}`);
    }
  } catch (e) {
    console.error("Failed to execute type checking:", e.message);
    console.error("Command:", `tscw ${command}`);
    throw e;
  }
}


/**
 *
 * @param {string} fullPath
 * @param {string[]} excludedDirs
 */
function shouldExcludeDir(fullPath, excludedDirs) {
  return excludedDirs.some((excludedDir) => {
    const normalizedExcludedDir = normalize(excludedDir);
    const normalizedPath = normalize(fullPath);
    return (
      normalizedExcludedDir === normalizedPath ||
      normalizedPath
        .split(sep)
        .filter((segment) => segment)
        .includes(normalizedExcludedDir)
    );
  });
}

/**
 * @param {string} dir
 * @param {RegExp} regex
 * @param {string[]} excludedDirs
 *
 * @returns {Promise<string[]>}
 */
async function getFilesRecursively(dir, regex, excludedDirs) {
  try {
    const files = await readdir(dir, { withFileTypes: true });
    const recursivePromises = [];
    const result = [];

    for (const file of files) {
      const fullPath = join(dir, file.name);

      if (file.isDirectory() && !shouldExcludeDir(fullPath, excludedDirs)) {
        recursivePromises.push(
          getFilesRecursively(fullPath, regex, excludedDirs)
        );
      } else if (regex.test(file.name)) {
        result.push(fullPath);
      }
    }

    const recursiveResults = await Promise.all(recursivePromises);
    return result.concat(...recursiveResults);
  } catch (e) {
    console.error(`Error reading directory: ${dir}`);
    console.error(e);
    exit(1);
  }
}

/**
 *
 * @param {string} packageArg
 * @returns {Promise<string>}
 */
async function getPackage(packageArg) {
  const packageDir = packageArg.split("=")[1].replace(/\/$/, "");
  try {
    const stats = await stat(packageDir);
    if (!stats.isDirectory()) {
      console.error(
        `Please specify a valid package, ${packageDir} is not a directory.`
      );
      exit(1);
    }
  } catch (e) {
    console.error(`Error reading package: ${packageDir}`);
    console.error(e);
    exit(1);
  }
  return packageDir;
}

/**
 *
 * @param {string | undefined} excludeDeclarationDirArg
 * @returns {string[]}
 */
function getExcludedDeclarationDirs(excludeDeclarationDirArg) {
  const excludedDirs = ["node_modules"];

  return !excludeDeclarationDirArg
    ? excludedDirs
    : excludeDeclarationDirArg
        .split("=")[1]
        .split(",")
        .map((dir) => dir.replace(/\/$/, "").trim())
        .concat(excludedDirs);
}

/**
 *
 * @param {string[]} args
 * @param {RegExp[]} regexes
 * @returns {{ matchedArgs: (string | undefined)[], remainingArgs: string[] }}
 */
function extractArgs(args, regexes) {
  /**
   * @type {(string | undefined)[]}
   */
  const matchedArgs = [];
  const remainingArgs = [...args];

  regexes.forEach((regex) => {
    const index = remainingArgs.findIndex((arg) => regex.test(arg));
    if (index !== -1) {
      const [arg] = remainingArgs.splice(index, 1);
      matchedArgs.push(arg);
    } else {
      matchedArgs.push(undefined);
    }
  });

  return { matchedArgs, remainingArgs };
}

/**
 * Remove the package segment from path.
 *
 * For example: `ax-bi-frontend/foo/bar.ts` -> `foo/bar.ts`
 *
 * @param {string[]} args
 * @param {string} package
 * @returns {string[]}
 */
function removePackageSegment(args, package) {
  const packageSegment = package.concat(sep);
  return args.map((arg) => {
    const normalizedPath = normalize(arg);

    if (normalizedPath.startsWith(packageSegment)) {
      return normalizedPath.slice(packageSegment.length);
    }
    return arg;
  });
}

/**
 * Resolve a changed file argument against the package root unless it is already
 * absolute. Pre-commit hooks can pass deleted files, so callers should skip
 * missing paths before invoking TypeScript.
 *
 * @param {string} file
 * @param {string} packageRootDir
 */
function resolveChangedFile(file, packageRootDir) {
  return isAbsolute(file) ? file : join(AXBI_ROOT, packageRootDir, file);
}

/**
 *
 * @param {string[]} files
 * @param {string} packageRootDir
 * @returns {string[]}
 */
function filterExistingFiles(files, packageRootDir) {
  const existingFiles = [];
  const missingFiles = [];

  files.forEach((file) => {
    if (existsSync(resolveChangedFile(file, packageRootDir))) {
      existingFiles.push(file);
    } else {
      missingFiles.push(file);
    }
  });

  if (missingFiles.length > 0) {
    const fileLabel = missingFiles.length === 1 ? "file" : "files";
    console.log(`Skipping ${missingFiles.length} missing changed ${fileLabel}:`);
    missingFiles.forEach((file) => console.log(`  ${file}`));
  }

  return existingFiles;
}

/**
 *
 * @param {string} dir
 */
function getTsConfig(dir) {
  const defaultTsConfig = "tsconfig.json";
  const tsConfig = join(dir, defaultTsConfig);

  if (!existsSync(tsConfig)) {
    console.error(`Error: ${defaultTsConfig} not found in ${dir}`);
    exit(1);
  }
  return tsConfig;
}

/**
 *
 * @param {string} module
 */
function packageRequire(module) {
  try {
    const localRequire = createRequire(join(cwd(), "node_modules"));
    return localRequire(module);
  } catch (e) {
    console.error(
      `Error: ${module} is not installed in ${cwd()}. Please install it first.`
    );
    exit(1);
  }
}
