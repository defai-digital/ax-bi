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
  Behavior,
  ChartMetadata,
  FeatureFlag,
  getChartMetadataRegistry,
  Preset,
  VizType,
} from '@ax-bi/ui-core';
import {
  render,
  cleanup,
  screen,
  userEvent,
  within,
  waitFor,
} from 'spec/helpers/testing-library';
import { DynamicPluginProvider } from 'src/components';
import { testWithId } from 'src/utils/testUtils';
import ChordChartPlugin from '../../../../../plugins/legacy-plugin-chart-chord/src';
import { BubbleChartPlugin } from '../../../../../plugins/legacy-preset-chart-nvd3/src';
import TableChartPlugin from '../../../../../plugins/plugin-chart-table/src';
import VizTypeGallery, { VIZ_TYPE_CONTROL_TEST_ID } from './VizTypeGallery';

// Mock scrollIntoView to avoid errors in test environment
jest.mock('scroll-into-view-if-needed', () => jest.fn());

class TestPreset extends Preset {
  constructor() {
    super({
      name: 'Gallery test charts',
      plugins: [
        new TableChartPlugin().configure({ key: VizType.Table }),
        new ChordChartPlugin().configure({ key: VizType.Chord }),
        new BubbleChartPlugin().configure({ key: VizType.LegacyBubble }),
      ],
    });
  }
}

new TestPreset().register();
getChartMetadataRegistry().registerValue(
  'test_chart_customization',
  new ChartMetadata({
    name: 'Test chart customization',
    behaviors: [Behavior.InteractiveChart, Behavior.ChartCustomization],
    tags: ['Experimental'],
    thumbnail: '',
  }),
);

const getTestId = testWithId<string>(VIZ_TYPE_CONTROL_TEST_ID, true);

const defaultProps = {
  onChange: jest.fn(),
  onDoubleClick: jest.fn(),
  selectedViz: null,
  denyList: [] as string[],
};

const renderGallery = () =>
  waitFor(() =>
    render(
      <DynamicPluginProvider>
        <VizTypeGallery {...defaultProps} />
      </DynamicPluginProvider>,
    ),
  );

const showAllCharts = async () => {
  const visualizations = screen.getByTestId(getTestId('viz-row'));
  userEvent.click(screen.getByRole('tab', { name: 'All charts' }));
  await within(visualizations).findByText('Table');
  return visualizations;
};

afterEach(() => {
  cleanup();
  jest.clearAllMocks();
  window.featureFlags = {};
});

test('legacy plugins are hidden from the gallery when LEGACY_CHART_PLUGINS is off', async () => {
  window.featureFlags = {};
  await renderGallery();
  const visualizations = await showAllCharts();

  expect(within(visualizations).getByText('Table')).toBeInTheDocument();
  expect(
    within(visualizations).queryByText('Chord Diagram'),
  ).not.toBeInTheDocument();
  expect(
    within(visualizations).queryByText('Bubble Chart (legacy)'),
  ).not.toBeInTheDocument();
});

test('legacy plugins are absent from search results when LEGACY_CHART_PLUGINS is off', async () => {
  window.featureFlags = {};
  await renderGallery();
  const visualizations = screen.getByTestId(getTestId('viz-row'));

  userEvent.type(screen.getByTestId(getTestId('search-input')), 'chord');
  expect(
    within(visualizations).queryByText('Chord Diagram'),
  ).not.toBeInTheDocument();
});

test('legacy plugins are shown in the gallery when LEGACY_CHART_PLUGINS is on', async () => {
  window.featureFlags = {
    [FeatureFlag.LegacyChartPlugins]: true,
  };
  await renderGallery();
  const visualizations = await showAllCharts();

  expect(within(visualizations).getByText('Table')).toBeInTheDocument();
  expect(
    await within(visualizations).findByText('Chord Diagram'),
  ).toBeInTheDocument();
  expect(
    within(visualizations).getByText('Bubble Chart (legacy)'),
  ).toBeInTheDocument();
});

test('chart customization plugins are hidden from the gallery and search', async () => {
  await renderGallery();
  const visualizations = await showAllCharts();

  expect(
    within(visualizations).queryByText('Test chart customization'),
  ).not.toBeInTheDocument();

  userEvent.type(
    screen.getByTestId(getTestId('search-input')),
    'Test chart customization',
  );
  expect(
    within(visualizations).queryByText('Test chart customization'),
  ).not.toBeInTheDocument();
});
