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
import type { AxBITheme } from '@ax-bi/core/theme';
import { render, screen, userEvent } from '@ax-bi/ui-core/spec';
import {
  EmptyCallout,
  EmptyCalloutText,
  EmptyCalloutTitle,
  Eyebrow,
  Hero,
  HeroText,
  HeroTitle,
  Page,
  PageNarrow,
  Panel,
  QuickAction,
  QuickActionGrid,
  Section,
  SectionDescription,
  SectionHeader,
  SectionTitle,
  softShadow,
  Stat,
  StatsGrid,
} from '.';

const lightTheme = {
  sizeUnit: 4,
  colorBgContainer: '#ffffff',
} as AxBITheme;

const darkTheme = {
  sizeUnit: 4,
  colorBgContainer: '#171d22',
} as AxBITheme;

test('softShadow uses cool slate shadow in light mode', () => {
  const shadow = softShadow(lightTheme);
  expect(shadow).toContain('rgba(15, 23, 42');
  expect(shadow).not.toContain('rgba(0, 0, 0');
});

test('softShadow uses black alpha shadow in dark mode', () => {
  const shadow = softShadow(darkTheme);
  expect(shadow).toContain('rgba(0, 0, 0');
  expect(shadow).not.toContain('rgba(15, 23, 42');
});

test('softShadow hover is stronger than default', () => {
  const base = softShadow(lightTheme, 'default');
  const hover = softShadow(lightTheme, 'hover');
  expect(hover).not.toEqual(base);
  expect(hover).toContain('0.1');
});

test('Page and PageNarrow render children', () => {
  render(
    <Page>
      <span>Wide content</span>
      <PageNarrow>
        <span>Narrow content</span>
      </PageNarrow>
    </Page>,
  );
  expect(screen.getByText('Wide content')).toBeInTheDocument();
  expect(screen.getByText('Narrow content')).toBeInTheDocument();
});

test('Hero renders eyebrow, title, and text', () => {
  render(
    <Hero>
      <div>
        <Eyebrow>Workspace</Eyebrow>
        <HeroTitle>Build something</HeroTitle>
        <HeroText>Start from data.</HeroText>
      </div>
    </Hero>,
  );
  expect(screen.getByText('Workspace')).toBeInTheDocument();
  expect(
    screen.getByRole('heading', { name: 'Build something' }),
  ).toBeInTheDocument();
  expect(screen.getByText('Start from data.')).toBeInTheDocument();
});

test('Panel and Section render with section chrome', () => {
  render(
    <Section>
      <SectionHeader>
        <SectionTitle>Recents</SectionTitle>
      </SectionHeader>
      <SectionDescription>Continue where you left off.</SectionDescription>
      <Panel>Panel body</Panel>
    </Section>,
  );
  expect(screen.getByRole('heading', { name: 'Recents' })).toBeInTheDocument();
  expect(screen.getByText('Continue where you left off.')).toBeInTheDocument();
  expect(screen.getByText('Panel body')).toBeInTheDocument();
});

test('Stat renders label, value, and hint as a card by default', () => {
  render(
    <StatsGrid>
      <Stat label="Dashboards" value={3} hint="Saved dashboards" />
    </StatsGrid>,
  );
  expect(screen.getByText('Dashboards')).toBeInTheDocument();
  expect(screen.getByText('3')).toBeInTheDocument();
  expect(screen.getByText('Saved dashboards')).toBeInTheDocument();
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
});

test('Stat renders a button and fires onClick when clickable', async () => {
  const onClick = jest.fn();
  render(
    <Stat
      label="Charts"
      value={7}
      onClick={onClick}
      aria-label="Browse charts"
    />,
  );
  const button = screen.getByRole('button', { name: 'Browse charts' });
  await userEvent.click(button);
  expect(onClick).toHaveBeenCalledTimes(1);
});

test('QuickAction renders action content inside a grid', () => {
  render(
    <QuickActionGrid>
      <QuickAction type="button">
        <span className="quick-action-icon">icon</span>
        <span>
          <div className="quick-action-title">Search</div>
          <div className="quick-action-text">Find pages and actions.</div>
        </span>
      </QuickAction>
    </QuickActionGrid>,
  );
  expect(screen.getByRole('button')).toBeInTheDocument();
  expect(screen.getByText('Search')).toBeInTheDocument();
  expect(screen.getByText('Find pages and actions.')).toBeInTheDocument();
});

test('EmptyCallout renders title and text', () => {
  render(
    <EmptyCallout>
      <EmptyCalloutTitle>Your workspace is empty</EmptyCalloutTitle>
      <EmptyCalloutText>Upload a file to get started.</EmptyCalloutText>
    </EmptyCallout>,
  );
  expect(
    screen.getByRole('heading', { name: 'Your workspace is empty' }),
  ).toBeInTheDocument();
  expect(screen.getByText('Upload a file to get started.')).toBeInTheDocument();
});
