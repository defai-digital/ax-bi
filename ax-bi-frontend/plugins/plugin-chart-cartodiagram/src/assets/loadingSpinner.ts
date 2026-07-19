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

/**
 * AX BI branded loading spinner, matching the boot-splash animation in
 * axbi/templates/axbi/loading.svg. Exported as a data URI because the
 * OpenLayers chart layer renders plain DOM (no React), and SVG SMIL
 * animations also run when the SVG is loaded via an <img> element.
 */
const LOADING_SPINNER_SVG = `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" overflow="visible">
  <defs>
    <linearGradient id="axbi-ring-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#35c98d" />
      <stop offset="100%" stop-color="#1f2434" />
    </linearGradient>
  </defs>
  <circle cx="100" cy="100" r="80" fill="none" stroke="url(#axbi-ring-gradient)" stroke-width="3" stroke-dasharray="40 20" stroke-linecap="round" opacity="0.5">
    <animateTransform attributeName="transform" type="rotate" from="0 100 100" to="360 100 100" dur="4s" repeatCount="indefinite" />
  </circle>
  <circle cx="100" cy="100" r="65" fill="none" stroke="url(#axbi-ring-gradient)" stroke-width="2" stroke-dasharray="25 15" stroke-linecap="round" opacity="0.3">
    <animateTransform attributeName="transform" type="rotate" from="360 100 100" to="0 100 100" dur="3s" repeatCount="indefinite" />
  </circle>
  <circle cx="100" cy="100" r="40" fill="none" stroke="#35c98d" stroke-width="1.5" opacity="0.4">
    <animate attributeName="r" values="38;44;38" dur="2s" repeatCount="indefinite" />
    <animate attributeName="opacity" values="0.4;0.15;0.4" dur="2s" repeatCount="indefinite" />
  </circle>
  <g transform="translate(100, 100)">
    <animateTransform attributeName="transform" type="scale" values="1;1.06;1" dur="2s" repeatCount="indefinite" additive="sum" />
    <animateTransform attributeName="transform" type="translate" values="100 100;100 100;100 100" dur="2s" repeatCount="indefinite" additive="replace" />
    <text x="-30" y="12" text-anchor="middle" font-family="'IBM Plex Mono', 'SFMono-Regular', Consolas, monospace" font-weight="700" font-size="48" fill="#35c98d">{</text>
    <text x="2" y="12" text-anchor="middle" font-family="'IBM Plex Mono', 'SFMono-Regular', Consolas, monospace" font-weight="700" font-size="48" fill="#1f2434">&#946;</text>
    <text x="32" y="12" text-anchor="middle" font-family="'IBM Plex Mono', 'SFMono-Regular', Consolas, monospace" font-weight="700" font-size="48" fill="#1f2434">}</text>
  </g>
</svg>`;

const loadingSpinnerUrl = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(
  LOADING_SPINNER_SVG,
)}`;

export default loadingSpinnerUrl;
