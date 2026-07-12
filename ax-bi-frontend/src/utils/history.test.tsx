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
  unstable_HistoryRouter as HistoryRouter,
  Route,
  Routes,
} from 'react-router-dom';
import { render, screen } from 'spec/helpers/testing-library';
import { history, routerHistory } from './history';

test('shared history renders routes beneath an application basename', () => {
  const originalLocation = `${history.location.pathname}${history.location.search}${history.location.hash}`;
  history.replace('/app/prefix/login/');

  const result = render(
    <HistoryRouter basename="/app/prefix" history={routerHistory}>
      <Routes>
        <Route path="/login/" element={<div>Login route</div>} />
      </Routes>
    </HistoryRouter>,
  );

  try {
    expect(screen.getByText('Login route')).toBeInTheDocument();
    expect(history.createURL('/app/prefix/login/').pathname).toBe(
      '/app/prefix/login/',
    );
    expect(history.encodeLocation('/login/?next=%2F#form')).toEqual({
      pathname: '/login/',
      search: '?next=%2F',
      hash: '#form',
    });
  } finally {
    result.unmount();
    history.replace(originalLocation);
  }
});
