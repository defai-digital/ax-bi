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
import { render, screen, fireEvent, userEvent } from '@ax-bi/ui-core/spec';
import { Breadcrumbs } from '.';

const items = [
  { label: 'Dashboards', href: '/dashboard/list/' },
  { label: 'Analytics', href: '/dashboard/list/?tag=analytics' },
  { label: 'Sales dashboard' },
];

test('renders all crumb labels with separators', () => {
  render(<Breadcrumbs items={items} />);

  expect(screen.getByText('Dashboards')).toBeInTheDocument();
  expect(screen.getByText('Analytics')).toBeInTheDocument();
  expect(screen.getByText('Sales dashboard')).toBeInTheDocument();
  expect(screen.getAllByText('/')).toHaveLength(2);
});

test('renders items with href as links', () => {
  render(<Breadcrumbs items={items} />);

  expect(screen.getByRole('link', { name: 'Dashboards' })).toHaveAttribute(
    'href',
    '/dashboard/list/',
  );
  expect(screen.getByRole('link', { name: 'Analytics' })).toHaveAttribute(
    'href',
    '/dashboard/list/?tag=analytics',
  );
});

test('renders the last item as the current page without a link', () => {
  render(<Breadcrumbs items={items} />);

  const current = screen.getByText('Sales dashboard');
  expect(current.closest('a')).toBeNull();
});

test('does not link the last item even when it has an href', () => {
  render(
    <Breadcrumbs
      items={[
        { label: 'Dashboards', href: '/dashboard/list/' },
        { label: 'Sales dashboard', href: '/dashboard/1/' },
      ]}
    />,
  );

  expect(screen.queryByRole('link', { name: 'Sales dashboard' })).toBeNull();
});

test('clicking a link calls onNavigate with the href and prevents default', () => {
  const onNavigate = jest.fn();
  render(<Breadcrumbs items={items} onNavigate={onNavigate} />);

  const link = screen.getByRole('link', { name: 'Dashboards' });
  const event = fireEvent.click(link);

  expect(onNavigate).toHaveBeenCalledTimes(1);
  expect(onNavigate).toHaveBeenCalledWith('/dashboard/list/');
  // fireEvent.click returns false when default was prevented
  expect(event).toBe(false);
});

test('modifier clicks keep native anchor behavior', () => {
  const onNavigate = jest.fn();
  render(<Breadcrumbs items={items} onNavigate={onNavigate} />);

  const link = screen.getByRole('link', { name: 'Dashboards' });
  fireEvent.click(link, { metaKey: true });

  expect(onNavigate).not.toHaveBeenCalled();
});

test('navigates via anchor href when onNavigate is not provided', () => {
  render(<Breadcrumbs items={items} />);

  const link = screen.getByRole('link', { name: 'Dashboards' });
  expect(link).toHaveAttribute('href', '/dashboard/list/');

  userEvent.click(link);
  // No SPA handler: the anchor keeps its native navigation behavior
  expect(link).toBeInTheDocument();
});

test('renders a custom separator', () => {
  render(<Breadcrumbs items={items} separator=">" />);

  expect(screen.getAllByText('>')).toHaveLength(2);
});
