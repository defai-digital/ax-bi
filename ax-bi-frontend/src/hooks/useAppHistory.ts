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
import { useContext, useEffect, useMemo, useState } from 'react';
import { UNSAFE_NavigationContext } from 'react-router-dom';
import type { History, Path as HistoryPath } from 'history';
import { history as historySingleton } from 'src/utils/history';

// history v5 removed LocationDescriptor/LocationState; define locally.
type LocationState = unknown;
type LocationDescriptor = Partial<HistoryPath> & { state?: LocationState };
type Path = string | LocationDescriptor;

type HistoryLike = Pick<
  History,
  | 'push'
  | 'replace'
  | 'go'
  | 'back'
  | 'forward'
  | 'block'
  | 'listen'
  | 'createHref'
  | 'action'
  | 'location'
>;

function asHistoryLike(navigator: unknown): HistoryLike | null {
  if (
    navigator &&
    typeof navigator === 'object' &&
    'push' in navigator &&
    typeof (navigator as History).push === 'function' &&
    'block' in navigator &&
    typeof (navigator as History).block === 'function'
  ) {
    return navigator as HistoryLike;
  }
  return null;
}

/**
 * React-router v5-compatible `useHistory`.
 *
 * Uses the HistoryRouter navigator when present (tests / app shell), otherwise
 * the shared browser history singleton. Avoids `useNavigate` so components can
 * render outside a Router (e.g. chart context menus in unit tests).
 */
export function useAppHistory() {
  const navigationContext = useContext(UNSAFE_NavigationContext);
  const activeHistory =
    asHistoryLike(navigationContext?.navigator) ?? historySingleton;
  const [location, setLocation] = useState(activeHistory.location);

  useEffect(() => {
    setLocation(activeHistory.location);
    return activeHistory.listen(({ location: next }) => {
      setLocation(next);
    });
  }, [activeHistory]);

  return useMemo(() => {
    // history v5's push/replace always take state as the *second* argument.
    // When the second arg is omitted, getNextLocation sets state to null and
    // overwrites any state embedded on a location object — so call sites like
    // history.push({ pathname, state: { requestedQuery } }) would lose payload.
    const push = (path: Path, state?: LocationState) => {
      if (typeof path === 'string') {
        activeHistory.push(path, state);
        return;
      }
      const { state: pathState, ...to } = path;
      activeHistory.push(to, state !== undefined ? state : pathState);
    };

    const replace = (path: Path, state?: LocationState) => {
      if (typeof path === 'string') {
        activeHistory.replace(path, state);
        return;
      }
      const { state: pathState, ...to } = path;
      activeHistory.replace(to, state !== undefined ? state : pathState);
    };

    return {
      push,
      replace,
      go: (n: number) => activeHistory.go(n),
      goBack: () => activeHistory.back(),
      goForward: () => activeHistory.forward(),
      location,
      length: window.history.length,
      action: activeHistory.action,
      block: activeHistory.block.bind(activeHistory),
      listen: activeHistory.listen.bind(activeHistory),
      createHref: activeHistory.createHref.bind(activeHistory),
    };
  }, [activeHistory, location]);
}

/** Alias for call sites still using the v5 name. */
export const useHistory = useAppHistory;
