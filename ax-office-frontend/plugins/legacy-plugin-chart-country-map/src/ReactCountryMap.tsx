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
import { reactify } from '@superset-ui/core';
import { styled } from '@apache-superset/core/theme';
import Component from './CountryMap';

// Type-erase the render function to allow flexible prop spreading in the wrapper.
// The CountryMap render function has typed props, but the wrapper passes props via spread
// which TypeScript cannot verify at compile time. Props are validated at runtime.
const ReactComponent = reactify(
  Component as unknown as (
    container: HTMLDivElement,
    props: Record<string, unknown>,
  ) => void,
);

interface CountryMapWrapperProps {
  className?: string;
  [key: string]: unknown;
}

const CountryMap = ({
  className = '',
  ...otherProps
}: CountryMapWrapperProps) => (
  <div className={className}>
    <ReactComponent {...otherProps} />
  </div>
);

export default styled(CountryMap)`
  ${({ theme }) => `
    .superset-legacy-chart-country-map svg {
      background-color: ${theme.colorBgContainer};
    }

    .superset-legacy-chart-country-map {
      position: relative;
    }

    .superset-legacy-chart-country-map .background {
      fill: ${theme.colorBgContainer};
      pointer-events: all;
    }

    .superset-legacy-chart-country-map .hover-popup {
      position: absolute;
      color: ${theme.colorTextSecondary};
      display: none;
      padding: 4px;
      border-radius: 1px;
      background-color: ${theme.colorBgElevated};
      box-shadow: ${theme.boxShadow};
      font-size: 12px;
      border: 1px solid ${theme.colorBorder};
      z-index: 10001;
    }

    .superset-legacy-chart-country-map .country-map-inline-legend {
      position: absolute;
      left: ${theme.sizeUnit * 3}px;
      bottom: ${theme.sizeUnit * 3}px;
      z-index: 1;
      max-width: min(360px, calc(100% - ${theme.sizeUnit * 6}px));
      padding: ${theme.sizeUnit * 2}px ${theme.sizeUnit * 3}px;
      border: 1px solid ${theme.colorSplit};
      border-radius: ${theme.borderRadius}px;
      background: ${theme.colorBgElevated};
      color: ${theme.colorTextSecondary};
      box-shadow: ${theme.boxShadowSecondary};
      font-size: ${theme.fontSizeSM}px;
      line-height: 1.35;
      pointer-events: none;
    }

    .superset-legacy-chart-country-map .country-map-inline-legend-title {
      margin-bottom: ${theme.sizeUnit}px;
      color: ${theme.colorText};
      font-weight: ${theme.fontWeightStrong};
    }

    .superset-legacy-chart-country-map .country-map-inline-legend-row {
      display: flex;
      align-items: center;
      gap: ${theme.sizeUnit * 2}px;
      min-width: 0;
    }

    .superset-legacy-chart-country-map .country-map-inline-legend-row + .country-map-inline-legend-row {
      margin-top: ${theme.sizeUnit}px;
    }

    .superset-legacy-chart-country-map .country-map-inline-legend-gradient {
      width: ${theme.sizeUnit * 12}px;
      height: ${theme.sizeUnit * 2}px;
      flex: 0 0 auto;
      border-radius: ${theme.borderRadiusSM}px;
    }

    .superset-legacy-chart-country-map .country-map-inline-legend-empty {
      width: ${theme.sizeUnit * 3}px;
      height: ${theme.sizeUnit * 3}px;
      flex: 0 0 auto;
      border: 1px solid ${theme.colorBorder};
      border-radius: ${theme.borderRadiusSM}px;
    }

    .superset-legacy-chart-country-map .map-layer {
      fill: ${theme.colorBgContainer};
      stroke: ${theme.colorBorderSecondary};
      pointer-events: all;
    }

    .superset-legacy-chart-country-map .effect-layer {
      pointer-events: none;
    }

    .superset-legacy-chart-country-map path.region {
      cursor: pointer;
      stroke: ${theme.colorSplit};
    }

    .superset-legacy-chart-country-map .hover-popup.popup-at-bottom {
      transform: translateY(-150%);
    }

  `}
`;
