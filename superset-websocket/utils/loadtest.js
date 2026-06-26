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
const Redis = require('ioredis');
const { randomUUID } = require('crypto');

const numClients = 256;

function loadConfig() {
  try {
    return require('../config.json');
  } catch (error) {
    if (error.code !== 'MODULE_NOT_FOUND') {
      throw error;
    }
    return require('../config.example.json');
  }
}

function pushData(redis, config) {
  const globalEventStreamName = `${config.redisStreamPrefix}full`;

  for (let i = 0; i < numClients; i++) {
    const channelId = String(i);
    const streamId = `${config.redisStreamPrefix}${channelId}`;
    const data = {
      channel_id: channelId,
      job_id: randomUUID(),
      status: 'pending',
    };

    // push to channel stream
    redis
      .xadd(streamId, 'MAXLEN', 1000, '*', 'data', JSON.stringify(data))
      .then(resp => {
        console.log('stream response', resp);
      });

    // push to firehose (all events) stream
    redis
      .xadd(
        globalEventStreamName,
        'MAXLEN',
        100000,
        '*',
        'data',
        JSON.stringify(data),
      )
      .then(resp => {
        console.log('stream response', resp);
      });
  }
}

function start() {
  const config = loadConfig();
  const redis = new Redis(config.redis);
  pushData(redis, config);
  return setInterval(() => pushData(redis, config), 1000);
}

function printUsage() {
  console.log('Usage: node utils/loadtest.js');
  console.log('Writes async event test data to the configured Redis streams.');
}

if (require.main === module) {
  if (process.argv.includes('--help') || process.argv.includes('-h')) {
    printUsage();
  } else {
    start();
  }
}

module.exports = {
  loadConfig,
  printUsage,
  pushData,
  start,
};
