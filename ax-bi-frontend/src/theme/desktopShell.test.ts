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
import {
  DESKTOP_THEME_MESSAGE_SOURCE,
  WEB_THEME_MESSAGE_SOURCE,
} from './desktopThemeBridge';
import {
  getDesktopShellStatus,
  isDesktopShellActive,
  markDesktopShellActive,
  parseDesktopShellHello,
  postDesktopShellAction,
  SHELL_HELLO_MESSAGE_TYPE,
  SHELL_OPEN_HOME_MESSAGE_TYPE,
  SHELL_OPEN_SETTINGS_MESSAGE_TYPE,
} from './desktopShell';

test('parseDesktopShellHello accepts valid shell hello payloads', () => {
  expect(
    parseDesktopShellHello({
      source: DESKTOP_THEME_MESSAGE_SOURCE,
      type: SHELL_HELLO_MESSAGE_TYPE,
      status: 'Local · Ready',
    }),
  ).toEqual({ status: 'Local · Ready' });

  expect(
    parseDesktopShellHello({
      source: DESKTOP_THEME_MESSAGE_SOURCE,
      type: SHELL_HELLO_MESSAGE_TYPE,
    }),
  ).toEqual({ status: null });

  expect(
    parseDesktopShellHello({
      source: WEB_THEME_MESSAGE_SOURCE,
      type: SHELL_HELLO_MESSAGE_TYPE,
    }),
  ).toBeNull();
});

test('markDesktopShellActive persists shell presence for the session', () => {
  window.sessionStorage.clear();
  expect(isDesktopShellActive()).toBe(false);

  markDesktopShellActive('Local · Ready');
  expect(isDesktopShellActive()).toBe(true);
  expect(getDesktopShellStatus()).toBe('Local · Ready');
});

test('postDesktopShellAction posts to parent when framed', () => {
  const postMessage = jest.fn();
  const originalParent = window.parent;
  Object.defineProperty(window, 'parent', {
    configurable: true,
    value: { postMessage },
  });

  expect(postDesktopShellAction(SHELL_OPEN_HOME_MESSAGE_TYPE)).toBe(true);
  expect(postMessage).toHaveBeenCalledWith(
    {
      source: WEB_THEME_MESSAGE_SOURCE,
      type: SHELL_OPEN_HOME_MESSAGE_TYPE,
    },
    '*',
  );

  expect(postDesktopShellAction(SHELL_OPEN_SETTINGS_MESSAGE_TYPE)).toBe(true);

  Object.defineProperty(window, 'parent', {
    configurable: true,
    value: originalParent,
  });
});
