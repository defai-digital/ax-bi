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
 * Strips the configured JSX attributes (e.g. data-test) from production
 * builds. Local replacement for babel-plugin-jsx-remove-data-test-id, which
 * calls the t.jSXOpeningElement builder alias that @babel/core 8 removed.
 * Attribute names are matched exactly, mirroring the original plugin.
 */
module.exports = function removeDataTestAttributes() {
  return {
    name: 'remove-data-test-attributes',
    visitor: {
      JSXOpeningElement(path, state) {
        const attributes = (state.opts && state.opts.attributes) || [];
        if (!attributes.length) {
          return;
        }
        path.node.attributes = path.node.attributes.filter(
          attr =>
            !(
              attr.type === 'JSXAttribute' &&
              attr.name &&
              attr.name.type === 'JSXIdentifier' &&
              attributes.includes(attr.name.name)
            ),
        );
      },
    },
  };
};
