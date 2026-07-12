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
 * AX BI MCP Server
 *
 * Entry point for the MCP server when used as a Node.js module.
 */

const { spawn } = require('child_process');
const path = require('path');

class AXBIMCPServer {
    constructor(options = {}) {
        this.options = {
            transport: options.transport || 'http',
            host: options.host || '127.0.0.1',
            port: options.port || 5008,
            debug: options.debug || false,
            pythonPath: options.pythonPath || null,
            axbiRoot: options.axbiRoot || null,
            configPath: options.configPath || null,
        };
        this.process = null;
    }

    start() {
        const args =
            this.options.transport === 'stdio'
                ? ['--stdio']
                : [
                      '--http',
                      '--host',
                      String(this.options.host),
                      '--port',
                      String(this.options.port),
                  ];
        const env = { ...process.env };

        if (this.options.debug) {
            args.push('--debug');
            env.MCP_DEBUG = '1';
        }
        if (this.options.pythonPath) {
            env.PYTHONPATH = this.options.pythonPath;
        } else if (this.options.axbiRoot) {
            env.PYTHONPATH = this.options.axbiRoot;
        }
        if (this.options.configPath) {
            env.AXBI_CONFIG_PATH = this.options.configPath;
        }

        this.process = spawn(
            process.execPath,
            [path.join(__dirname, 'bin', 'ax-bi-mcp.js'), ...args],
            {
                env,
                cwd: this.options.axbiRoot || process.cwd(),
                stdio: 'inherit',
            },
        );
        return this.process;
    }

    stop() {
        if (this.process) {
            this.process.kill();
            this.process = null;
        }
    }
}

module.exports = AXBIMCPServer;
