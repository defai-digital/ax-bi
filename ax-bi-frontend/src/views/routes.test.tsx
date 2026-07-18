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
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { render, screen } from 'spec/helpers/testing-library';
import { isFrontendRoute, routes } from './routes';

jest.mock('src/pages/Home', () => () => <div data-test="mock-home" />);

// eslint-disable-next-line no-restricted-globals -- TODO: Migrate from describe blocks
describe('isFrontendRoute', () => {
  test('returns true if a route matches', () => {
    routes.forEach(r => {
      expect(isFrontendRoute(r.path)).toBe(true);
    });
  });

  test('returns false if a route does not match', () => {
    expect(isFrontendRoute('/nonexistent/path/')).toBe(false);
  });
});

const legacyRedirects: Record<string, string> = {
  '/tablemodelview/list/': '/datasets',
  '/databaseview/list/': '/databases',
  '/savedqueryview/list/': '/saved-queries',
  '/csstemplatemodelview/list/': '/css-templates',
};

const LocationProbe = () => {
  const { pathname, search } = useLocation();
  return <div data-test="location-probe">{`${pathname}${search}`}</div>;
};

test('canonical resource routes exist and stay frontend routes', () => {
  Object.values(legacyRedirects).forEach(canonicalPath => {
    expect(routes.some(r => r.path === canonicalPath)).toBe(true);
    expect(isFrontendRoute(canonicalPath)).toBe(true);
  });
});

test('legacy routes remain registered as frontend routes', () => {
  Object.keys(legacyRedirects).forEach(legacyPath => {
    expect(isFrontendRoute(legacyPath)).toBe(true);
  });
});

test.each(Object.entries(legacyRedirects))(
  'legacy route %s redirects to %s preserving the query string',
  (legacyPath, canonicalPath) => {
    const route = routes.find(r => r.path === legacyPath);
    expect(route).toBeDefined();
    const RedirectComponent = route!.Component;
    render(
      <MemoryRouter initialEntries={[`${legacyPath}?pageIndex=2`]}>
        <LocationProbe />
        <Routes>
          <Route
            path={legacyPath}
            element={<RedirectComponent {...route!.props} />}
          />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByTestId('location-probe')).toHaveTextContent(
      `${canonicalPath}?pageIndex=2`,
    );
  },
);

test('legacy redirect preserves hash and location state', () => {
  const route = routes.find(r => r.path === '/tablemodelview/list/');
  expect(route).toBeDefined();
  const RedirectComponent = route!.Component;

  const HashStateProbe = () => {
    const { pathname, hash, state } = useLocation();
    return (
      <div data-test="hash-state-probe">
        {`${pathname}${hash}|${JSON.stringify(state)}`}
      </div>
    );
  };

  render(
    <MemoryRouter
      initialEntries={[
        {
          pathname: '/tablemodelview/list/',
          hash: '#row-7',
          state: { from: 'palette' },
        },
      ]}
    >
      <HashStateProbe />
      <Routes>
        <Route
          path="/tablemodelview/list/"
          element={<RedirectComponent {...route!.props} />}
        />
      </Routes>
    </MemoryRouter>,
  );

  expect(screen.getByTestId('hash-state-probe')).toHaveTextContent(
    '/datasets#row-7|{"from":"palette"}',
  );
});
