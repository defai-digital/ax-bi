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

/**
 * AX BI MCP (Model Context Protocol) Server Runner
 *
 * OVERVIEW:
 * This Node.js wrapper script provides an npx-compatible entry point for the AX BI MCP service.
 * It acts as a bridge between npm/npx tooling and the Python-based MCP server implementation.
 *
 * FUNCTIONALITY:
 * - Detects and validates Python environment and AxBI installation
 * - Supports both stdio (Claude Desktop integration) and HTTP transport modes
 * - Handles command-line argument parsing and environment variable configuration
 * - Manages Python subprocess lifecycle with proper signal handling
 * - Provides comprehensive help documentation and error diagnostics
 *
 * USAGE PATTERNS (DEVELOPMENT - Not yet published to npm):
 * - Direct execution: node axbi/mcp_service/bin/ax-bi-mcp.js --stdio
 * - HTTP server: node axbi/mcp_service/bin/ax-bi-mcp.js --http --port 6000
 * - Development debugging: node axbi/mcp_service/bin/ax-bi-mcp.js --debug
 *
 * FUTURE USAGE (Once published to npm registry):
 * - npx @ax-bi/mcp-server --stdio
 * - npx @ax-bi/mcp-server --http --port 6000
 *
 * ARCHITECTURE:
 * This wrapper enables the MCP service to be distributed as an npm package while
 * maintaining the core Python implementation, bridging Node.js tooling with Python execution.
 *
 * PACKAGE STATUS (as of 2025-01-10):
 * - NOT YET PUBLISHED to npm registry
 * - Package name reserved: @ax-bi/mcp-server
 * - Requires package.json with proper metadata and "bin" field for npx execution
 * - Will need to be published to npm registry before npx commands work
 *
 * TODO FOR NPM PUBLISHING:
 * 1. Create package.json with name "@ax-bi/mcp-server"
 * 2. Add "bin" field pointing to this file
 * 3. Set version, description, repository, license
 * 4. Run npm publish with appropriate access rights
 */

const { spawn, execSync, execFileSync } = require('child_process');
const path = require('path');
const fs = require('fs');

// Parse command line arguments
const args = process.argv.slice(2);
const isStdio = args.includes('--stdio') || process.env.FASTMCP_TRANSPORT === 'stdio';
const isDebug = args.includes('--debug') || process.env.MCP_DEBUG === '1';
const showHelp = args.includes('--help') || args.includes('-h');

// Configuration
const DEFAULT_PORT = process.env.MCP_PORT || '5008';
const DEFAULT_HOST = process.env.MCP_HOST || '127.0.0.1';

function getOptionValue(name, defaultValue) {
    const optionIndex = args.indexOf(name);
    if (optionIndex === -1) {
        return defaultValue;
    }

    const value = args[optionIndex + 1];
    if (!value || value.startsWith('--')) {
        console.error(`Error: ${name} requires a value`);
        process.exit(1);
    }

    return value;
}

function validateArgs() {
    const optionsWithValues = new Set(['--port', '--host']);
    const flagOptions = new Set(['--stdio', '--http', '--debug', '--help', '-h']);

    for (let index = 0; index < args.length; index += 1) {
        const arg = args[index];

        if (optionsWithValues.has(arg)) {
            const value = args[index + 1];
            if (!value || value.startsWith('--')) {
                console.error(`Error: ${arg} requires a value`);
                process.exit(1);
            }
            index += 1;
            continue;
        }

        if (flagOptions.has(arg)) {
            continue;
        }

        console.error(`Error: Unknown option: ${arg}`);
        console.error('Run with --help to see supported options.');
        process.exit(1);
    }
}

function printHelp() {
    console.log(`
AX BI MCP Server

Usage:
  Development: node axbi/mcp_service/bin/ax-bi-mcp.js [options]
  Future (npm): npx @ax-bi/mcp-server [options]

Options:
  --stdio       Run in stdio mode for direct Claude Desktop integration
  --http        Run in HTTP mode (default)
  --port PORT   HTTP port to bind to (default: ${DEFAULT_PORT})
  --host HOST   HTTP host to bind to (default: ${DEFAULT_HOST})
  --debug       Enable debug mode
  --help        Show this help message

Environment Variables:
  FASTMCP_TRANSPORT     Transport mode (stdio or http)
  MCP_PORT              HTTP port (default: ${DEFAULT_PORT})
  MCP_HOST              HTTP host (default: ${DEFAULT_HOST})
  MCP_DEBUG             Enable debug (set to 1)
  PYTHONPATH            Python path including AxBI root
  AXBI_CONFIG_PATH  Path to axbi_config.py

Examples (Development):
  # Run in stdio mode for Claude Desktop
  node axbi/mcp_service/bin/ax-bi-mcp.js --stdio

  # Run in HTTP mode on custom port
  node axbi/mcp_service/bin/ax-bi-mcp.js --http --port 6000

  # Run with debug output
  node axbi/mcp_service/bin/ax-bi-mcp.js --debug

  # Or use the Python CLI directly:
  ax-bi mcp run --host 127.0.0.1 --port 6000
`);
}

// Find AxBI root directory
function findAxBIRoot() {
    // Start from the mcp_service directory
    let currentDir = path.resolve(__dirname, '..');

    // Walk up until we find the axbi root (contains setup.py or pyproject.toml)
    while (currentDir !== path.dirname(currentDir)) {
        if (fs.existsSync(path.join(currentDir, 'pyproject.toml')) ||
            fs.existsSync(path.join(currentDir, 'setup.py'))) {
            // Check if it's actually the axbi root (has axbi directory)
            if (fs.existsSync(path.join(currentDir, 'axbi'))) {
                return currentDir;
            }
        }
        currentDir = path.dirname(currentDir);
    }

    // Fallback to environment variable
    if (process.env.PYTHONPATH) {
        return process.env.PYTHONPATH;
    }

    throw new Error('Could not find AxBI root directory. Please set PYTHONPATH environment variable.');
}

// Find Python executable
function findPython() {
    // Check for virtual environment in common locations
    const axbiRoot = findAxBIRoot();
    const venvPaths = [
        path.join(axbiRoot, 'venv', 'bin', 'python'),
        path.join(axbiRoot, '.venv', 'bin', 'python'),
        path.join(axbiRoot, 'venv', 'Scripts', 'python.exe'),
        path.join(axbiRoot, '.venv', 'Scripts', 'python.exe'),
    ];

    for (const venvPath of venvPaths) {
        if (fs.existsSync(venvPath)) {
            return venvPath;
        }
    }

    // Check if python3 is available
    try {
        execSync('python3 --version', { stdio: 'ignore' });
        return 'python3';
    } catch (e) {
        // Fall back to python
        return 'python';
    }
}

// Find AX BI CLI executable
function findAxBICli() {
    const axbiRoot = findAxBIRoot();
    const cliPaths = [
        path.join(axbiRoot, 'venv', 'bin', 'ax-bi'),
        path.join(axbiRoot, '.venv', 'bin', 'ax-bi'),
        path.join(axbiRoot, 'venv', 'Scripts', 'ax-bi.exe'),
        path.join(axbiRoot, '.venv', 'Scripts', 'ax-bi.exe'),
    ];

    for (const cliPath of cliPaths) {
        if (fs.existsSync(cliPath)) {
            return cliPath;
        }
    }

    try {
        execSync('ax-bi version', { stdio: 'ignore' });
        return 'ax-bi';
    } catch (e) {
        return null;
    }
}

// Check Python and AxBI installation
function checkEnvironment() {
    const python = findPython();
    const axbiRoot = findAxBIRoot();
    const axbiCli = findAxBICli();

        console.error(`Using Python: ${python}`);
        console.error(`AxBI root: ${axbiRoot}`);

    // Check if AxBI is installed
    try {
        execFileSync(python, ['-c', 'import axbi'], {
            env: { ...process.env, PYTHONPATH: axbiRoot },
            stdio: 'ignore'
        });
    } catch (e) {
        console.error(`
Error: AxBI is not installed or not accessible.

Please ensure:
1. You have activated your virtual environment
2. AxBI is installed (pip install -e .)
3. PYTHONPATH is set correctly

Current PYTHONPATH: ${axbiRoot}
`);
        process.exit(1);
    }

    return { python, axbiRoot, axbiCli };
}

// Main execution
function main() {
    const { python, axbiRoot, axbiCli } = checkEnvironment();

    // Prepare environment variables
    const env = {
        ...process.env,
        PYTHONPATH: axbiRoot,
        FASTMCP_TRANSPORT: isStdio ? 'stdio' : 'http',
    };

    if (!env.AXBI_CONFIG_PATH) {
        const configPath = path.join(axbiRoot, 'axbi_config.py');
        if (fs.existsSync(configPath)) {
            env.AXBI_CONFIG_PATH = configPath;
        }
    }

    if (isDebug) {
        env.MCP_DEBUG = '1';
    }

    // Prepare command and arguments
    let command;
    let commandArgs;
    if (isStdio) {
        console.error('Starting AX BI MCP server in STDIO mode...');
        command = python;
        commandArgs = ['-m', 'axbi.mcp_service'];
    } else {
        const port = getOptionValue('--port', DEFAULT_PORT);
        const host = getOptionValue('--host', DEFAULT_HOST);

        console.error(`Starting AX BI MCP server in HTTP mode on ${host}:${port}...`);
        if (!axbiCli) {
            console.error('Error: Could not find AX BI CLI executable.');
            process.exit(1);
        }

        command = axbiCli;
        commandArgs = [
            'mcp', 'run',
            '--host', host,
            '--port', port
        ];

        if (isDebug) {
            commandArgs.push('--debug');
        }
    }

    // Spawn the Python process
    const pythonProcess = spawn(command, commandArgs, {
        env,
        stdio: isStdio ? ['inherit', 'inherit', 'inherit'] : 'inherit',
        cwd: axbiRoot
    });

    // Handle process events
    pythonProcess.on('error', (err) => {
        console.error('Failed to start MCP server:', err);
        process.exit(1);
    });

    pythonProcess.on('exit', (code, signal) => {
        if (signal) {
            console.error(`MCP server terminated by signal: ${signal}`);
        } else if (code !== 0) {
            console.error(`MCP server exited with code: ${code}`);
        }
        process.exit(code || 0);
    });

    // Handle termination signals
    process.on('SIGINT', () => {
        pythonProcess.kill('SIGINT');
    });

    process.on('SIGTERM', () => {
        pythonProcess.kill('SIGTERM');
    });
}

if (require.main === module) {
    validateArgs();
    if (showHelp) {
        printHelp();
        process.exit(0);
    }
    main();
}

module.exports = {
    findPython,
    findAxBICli,
    findAxBIRoot,
    getOptionValue,
    main,
    printHelp,
};
