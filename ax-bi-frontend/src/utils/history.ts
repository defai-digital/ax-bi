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
import { createBrowserHistory, parsePath, type To } from 'history';
import type { HistoryRouterProps } from 'react-router-dom';

type RouterHistory = HistoryRouterProps['history'];
type RouterListener = Parameters<RouterHistory['listen']>[0];
type RouterUpdate = Parameters<RouterListener>[0];

/**
 * Shared browser history used with react-router's HistoryRouter. The adapter
 * methods satisfy React Router's history contract while preserving history v5
 * blocking and listening for SQL Lab and Explore unsaved-change flows.
 */
const browserHistory = createBrowserHistory();
const browserListen = browserHistory.listen.bind(browserHistory);

export const history = Object.assign(browserHistory, {
  createURL: (to: To) =>
    new URL(browserHistory.createHref(to), window.location.origin),
  encodeLocation: (to: To) => {
    const path = typeof to === 'string' ? parsePath(to) : to;
    return {
      pathname: path.pathname ?? '',
      search: path.search ?? '',
      hash: path.hash ?? '',
    };
  },
  listen: (listener: RouterListener) =>
    browserListen(update =>
      listener({ ...update, delta: null } as RouterUpdate),
    ),
});

export const routerHistory = history as unknown as RouterHistory;
