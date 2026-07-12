// @ts-nocheck
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
/* eslint-disable react/sort-prop-types */
import { select, pointer } from 'd3-selection';
import { zoom as d3Zoom, zoomIdentity } from 'd3-zoom';
import { geoPath, geoMercator, geoCentroid } from 'd3-geo';
import { rgb } from 'd3-color';
import { json as d3Json } from 'd3-fetch';
import { extent as d3Extent } from 'd3-array';
import {
  BinaryQueryObjectFilterClause,
  CategoricalColorNamespace,
  ContextMenuFilters,
  DataMask,
  ValueFormatter,
  getSequentialSchemeRegistry,
} from '@ax-bi/ui-core';
import countries, { countryOptions } from './countries';

/**
 * Escape HTML special characters to prevent XSS attacks
 */
function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

interface CountryMapDataItem {
  country_id: string;
  metric: number;
}

interface GeoFeature {
  properties: {
    ISO: string;
    ID_2?: string;
    NAME_1?: string;
    NAME_2?: string;
  };
}

interface GeoData {
  features: GeoFeature[];
}

interface CountryMapProps {
  data: CountryMapDataItem[];
  width: number;
  height: number;
  country: string;
  linearColorScheme: string;
  numberFormat?: string; // left for backward compatibility
  formatter: ValueFormatter;
  colorScheme: string;
  sliceId: number;
  onContextMenu?: (
    clientX: number,
    clientY: number,
    data: ContextMenuFilters,
  ) => void;
  emitCrossFilters?: boolean;
  setDataMask?: (dataMask: DataMask) => void;
  filterState?: {
    selectedValues?: string[];
    extraFormData?: {
      filters?: BinaryQueryObjectFilterClause[];
    };
  };
  entity?: string;
}

const maps: Record<string, GeoData> = {};
// Store zoom state per chart instance using element as key to enable garbage collection
const zoomStates = new WeakMap<
  HTMLElement,
  { scale: number; translate: [number, number] }
>();

function CountryMap(element: HTMLElement, props: CountryMapProps) {
  const {
    data,
    width,
    height,
    country,
    entity,
    linearColorScheme,
    formatter,
    colorScheme,
    sliceId,
    filterState,
    emitCrossFilters,
    onContextMenu,
    setDataMask,
  } = props;

  const container = element;
  const rawExtents = d3Extent(data, v => v.metric);
  const extents: [number, number] =
    rawExtents[0] != null && rawExtents[1] != null
      ? [rawExtents[0], rawExtents[1]]
      : [0, 1];
  const colorSchemeObj = getSequentialSchemeRegistry().get(linearColorScheme);
  const linearColorScale = colorSchemeObj
    ? colorSchemeObj.createLinearScale(extents)
    : () => '#ccc'; // fallback if scheme not found
  const colorScale = CategoricalColorNamespace.getScale(colorScheme);

  const colorMap: Record<string, string> = {};
  data.forEach(d => {
    colorMap[d.country_id] = colorScheme
      ? colorScale(d.country_id, sliceId)
      : (linearColorScale(d.metric) ?? '');
  });

  const colorFn = (feature: GeoFeature): string => {
    if (!feature?.properties) return '#d9d9d9';
    const iso = feature.properties.ISO;
    return colorMap[iso] || '#d9d9d9';
  };

  // Check if dashboard is in edit mode
  const isEditMode = container.closest('.dashboard--editing') !== null;

  const path = geoPath();
  const div = select(container);
  div.classed('axbi-legacy-chart-country-map', true);
  div.selectAll('*').remove();
  container.style.height = `${height}px`;
  container.style.width = `${width}px`;
  const svg = div
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .attr('preserveAspectRatio', 'xMidYMid meet');

  // Only set grab cursor if not in edit mode
  if (!isEditMode) {
    svg.style('cursor', 'grab');
  }
  svg
    .append('rect')
    .attr('class', 'background')
    .attr('width', width)
    .attr('height', height);
  const g = svg.append('g');
  const mapLayer = g.append('g').classed('map-layer', true);
  // Add hover popup for tooltip
  const hoverPopup = div.append('div').attr('class', 'hover-popup');
  const [minMetric, maxMetric] = extents;
  const lowColor = linearColorScale(minMetric) ?? '#99f6e4';
  const highColor = linearColorScale(maxMetric) ?? '#0f766e';
  const noDataColor = '#d9d9d9';

  div.append('div').attr('class', 'country-map-inline-legend').html(`
    <div class="country-map-inline-legend-title">Legend</div>
    <div class="country-map-inline-legend-row">
      <span
        class="country-map-inline-legend-gradient"
        style="background:linear-gradient(90deg, ${lowColor}, ${highColor})"
      ></span>
      <span>Region color: ${formatter(minMetric)} to ${formatter(maxMetric)}</span>
    </div>
    <div class="country-map-inline-legend-row">
      <span
        class="country-map-inline-legend-empty"
        style="background:${noDataColor}"
      ></span>
      <span>No color: no sales data</span>
    </div>
  `);

  // Track mouse position to distinguish clicks from drags
  let mousedownPos: { x: number; y: number } | null = null;

  // Cross-filter support
  const getCrossFilterDataMask = (
    source: GeoFeature,
  ): { dataMask: DataMask; isCurrentValueSelected: boolean } | undefined => {
    if (!entity) return undefined;

    const selected = filterState?.selectedValues || [];
    const iso = source?.properties?.ISO;
    if (!iso) return undefined;

    const isSelected = selected.includes(iso);
    const values = isSelected ? [] : [iso];

    return {
      dataMask: {
        extraFormData: {
          filters: values.length
            ? [{ col: entity, op: 'IN', val: values }]
            : [],
        },
        filterState: {
          value: values.length ? values : null,
          selectedValues: values.length ? values : null,
        },
      },
      isCurrentValueSelected: isSelected,
    };
  };

  // Handle right-click context menu
  const handleContextMenu = (event: MouseEvent, feature: GeoFeature): void => {
    if (typeof onContextMenu === 'function') {
      event?.preventDefault();
    }

    const iso = feature?.properties?.ISO;
    if (!iso || typeof onContextMenu !== 'function' || !entity) return;

    const drillVal = iso;
    const drillToDetailFilters = [
      { col: entity, op: '==', val: drillVal, formattedVal: drillVal },
    ];
    const drillByFilters = [{ col: entity, op: '==', val: drillVal }];

    onContextMenu(event.clientX, event.clientY, {
      drillToDetail: drillToDetailFilters,
      crossFilter: getCrossFilterDataMask(feature),
      drillBy: { filters: drillByFilters, groupbyFieldName: 'entity' },
    });
  };

  const getNameOfRegion = function getNameOfRegion(
    feature: GeoFeature,
  ): string {
    if (feature && feature.properties) {
      if (feature.properties.ID_2) {
        return feature.properties.NAME_2 || '';
      }
      return feature.properties.NAME_1 || '';
    }
    return '';
  };

  const updatePopupPosition = (event: MouseEvent): void => {
    const svgHeight = svg.node().getBoundingClientRect().height;
    const [x, y] = pointer(event, svg.node());
    hoverPopup
      .style('display', 'block')
      .style('top', `${y + 30}px`)
      .style('left', `${x}px`)
      .classed('popup-at-bottom', y > (svgHeight * 2) / 3);
  };

  const mouseenter = function mouseenter(
    this: SVGPathElement,
    event: MouseEvent,
    d: GeoFeature,
  ): void {
    // Darken color
    let c: string = colorFn(d);
    if (c) {
      c = rgb(c).darker().toString();
    }
    select(this).style('fill', c);

    // Display information popup
    const result = data.filter(r => r.country_id === d?.properties?.ISO);
    const regionName = escapeHtml(getNameOfRegion(d));
    const metricValue =
      result.length > 0 ? escapeHtml(String(formatter(result[0].metric))) : '';
    hoverPopup
      .style('display', 'block')
      .html(`<div><strong>${regionName}</strong><br>${metricValue}</div>`);
    updatePopupPosition(event);
  };

  // Mouse move handler to update tooltip position
  const mousemove = function mousemove(event: MouseEvent): void {
    updatePopupPosition(event);
  };

  const mouseout = function mouseout(this: SVGPathElement): void {
    select(this).style('fill', (d: GeoFeature) => colorFn(d));
    hoverPopup.style('display', 'none');
  };

  // Only enable zoom if not in edit mode
  if (!isEditMode) {
    const zoomBehavior = d3Zoom()
      .scaleExtent([1, 4])
      .on('start', () => {
        svg.style('cursor', 'grabbing');
      })
      .on('zoom', event => {
        const { transform } = event;
        const scale = transform.k;
        const scaledW = width * scale;
        const scaledH = height * scale;
        const minX = Math.min(0, width - scaledW);
        const maxX = 0;
        const minY = Math.min(0, height - scaledH);
        const maxY = 0;

        // Clamp pan so the map cannot be dragged off-canvas. Re-sync d3-zoom
        // when clamping so the next wheel/drag event does not jump.
        const tx = Math.max(Math.min(transform.x, maxX), minX);
        const ty = Math.max(Math.min(transform.y, maxY), minY);
        if (tx !== transform.x || ty !== transform.y) {
          // Re-entrancy: next zoom event has the clamped transform and falls
          // through to the visual update below.
          svg.call(
            zoomBehavior.transform,
            zoomIdentity.translate(tx, ty).scale(scale),
          );
          return;
        }

        g.attr('transform', transform.toString());
        const prev = zoomStates.get(element);
        const changed =
          !prev ||
          prev.scale !== scale ||
          prev.translate[0] !== tx ||
          prev.translate[1] !== ty;
        if (changed) {
          zoomStates.set(element, { scale, translate: [tx, ty] });
        }
      })
      .on('end', () => {
        svg.style('cursor', 'grab');
      });

    svg.call(zoomBehavior);

    // Restore previous zoom state if it exists
    const savedZoom = zoomStates.get(element);
    if (savedZoom) {
      const { scale, translate } = savedZoom;
      const restored = zoomIdentity
        .translate(translate[0], translate[1])
        .scale(scale);
      svg.call(zoomBehavior.transform, restored);
      g.attr('transform', restored.toString());
    }
  }

  // Visual highlighting for selected regions
  function highlightSelectedRegion(
    selectedValues: string[] | null = null,
  ): void {
    const selected = selectedValues || filterState?.selectedValues || [];

    mapLayer
      .selectAll('path.region')
      .style('fill-opacity', (d: GeoFeature) => {
        const iso = d?.properties?.ISO;
        return selected.length === 0 || selected.includes(iso) ? 1 : 0.3;
      })
      .style('stroke', (d: GeoFeature) => {
        const iso = d?.properties?.ISO;
        return selected.includes(iso) ? '#222' : null;
      })
      .style('stroke-width', (d: GeoFeature) => {
        const iso = d?.properties?.ISO;
        return selected.includes(iso) ? '1.5px' : '0.5px';
      });
  }

  // Click handler for cross-filters
  const handleClick = (feature: GeoFeature): void => {
    if (!entity || !emitCrossFilters || typeof setDataMask !== 'function') {
      return;
    }

    const result = getCrossFilterDataMask(feature);
    if (!result) return;

    const { dataMask, isCurrentValueSelected } = result;
    setDataMask(dataMask);

    const iso = feature?.properties?.ISO;
    const newSelection = isCurrentValueSelected || !iso ? [] : [iso];
    highlightSelectedRegion(newSelection);
  };

  function drawMap(mapData: GeoData): void {
    const { features } = mapData;
    const center = geoCentroid(mapData as any);
    const scale = 100;
    const projection = geoMercator()
      .scale(scale)
      .center(center)
      .translate([width / 2, height / 2]);
    path.projection(projection);

    const bounds = path.bounds(mapData as any);
    const hscale = (scale * width) / (bounds[1][0] - bounds[0][0]);
    const vscale = (scale * height) / (bounds[1][1] - bounds[0][1]);
    const newScale = Math.min(hscale, vscale);

    projection.scale(newScale);
    const newBounds = path.bounds(mapData as any);
    projection.translate([
      width - (newBounds[0][0] + newBounds[1][0]) / 2,
      height - (newBounds[0][1] + newBounds[1][1]) / 2,
    ]);

    const sel = mapLayer.selectAll('path.region').data(features);

    sel
      .enter()
      .append('path')
      .attr('class', 'region')
      .attr('vector-effect', 'non-scaling-stroke');

    // Apply attributes and event handlers to all elements (enter + update)
    mapLayer
      .selectAll('path.region')
      .attr('d', path)
      .style('fill', colorFn)
      .on('mouseenter', mouseenter)
      .on('mousemove', mousemove)
      .on('mouseout', mouseout)
      .on('contextmenu', handleContextMenu)
      .on('mousedown', function mousedown(event: MouseEvent) {
        const pos = pointer(event, svg.node());
        mousedownPos = { x: pos[0], y: pos[1] };
      })
      .on('click', function click(event: MouseEvent, feature: GeoFeature) {
        if (mousedownPos) {
          const pos = pointer(event, svg.node());
          const dx = Math.abs(pos[0] - mousedownPos.x);
          const dy = Math.abs(pos[1] - mousedownPos.y);
          const dragThreshold = 5;

          if (dx < dragThreshold && dy < dragThreshold) {
            handleClick(feature);
          }

          mousedownPos = null;
        }
      });

    sel.exit().remove();

    highlightSelectedRegion();
  }

  const map = maps[country];
  if (map) {
    drawMap(map);
  } else {
    const url = (countries as Record<string, string>)[country];
    if (!url) {
      const countryName =
        countryOptions.find(x => x[0] === country)?.[1] || country;
      select(element).html(
        `<div class="alert alert-danger">No map data available for ${escapeHtml(countryName)}</div>`,
      );
      return;
    }
    d3Json(url)
      .then((mapData: GeoData) => {
        maps[country] = mapData;
        drawMap(mapData);
      })
      .catch(() => {
        const countryName =
          countryOptions.find(x => x[0] === country)?.[1] || country;
        select(element).html(
          `<div class="alert alert-danger">Could not load map data for ${escapeHtml(countryName)}</div>`,
        );
      });
  }
}

CountryMap.displayName = 'CountryMap';

export default CountryMap;
