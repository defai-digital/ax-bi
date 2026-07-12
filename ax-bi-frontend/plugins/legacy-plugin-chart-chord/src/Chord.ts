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
/* eslint-disable no-param-reassign, react/sort-prop-types */
import { select, descending } from 'd3-selection';
import { chord as d3Chord, ribbon } from 'd3-chord';
import { arc as d3Arc } from 'd3-shape';
import { getNumberFormatter, CategoricalColorNamespace } from '@ax-bi/ui-core';

interface ChordData {
  matrix: number[][];
  nodes: string[];
}

interface ChordProps {
  data: ChordData;
  width: number;
  height: number;
  colorScheme: string;
  numberFormat: string;
  sliceId: number;
}

function Chord(element: HTMLElement, props: ChordProps) {
  const { data, width, height, numberFormat, colorScheme, sliceId } = props;

  element.innerHTML = '';

  const div = select(element);
  div.classed('axbi-legacy-chart-chord', true);
  const { nodes, matrix } = data;
  const f = getNumberFormatter(numberFormat);
  const colorFn = CategoricalColorNamespace.getScale(colorScheme);

  const outerRadius = Math.min(width, height) / 2 - 10;
  const innerRadius = outerRadius - 24;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let chordSel: any;

  const arc = d3Arc().innerRadius(innerRadius).outerRadius(outerRadius);

  const layout = d3Chord()
    .padAngle(0.04)
    .sortSubgroups(descending)
    .sortChords(descending);

  const ribbonPath = ribbon().radius(innerRadius);

  const svg = div
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .on('mouseout', () => chordSel.classed('fade', false))
    .append('g')
    .attr('id', 'circle')
    .attr('transform', `translate(${width / 2}, ${height / 2})`);

  svg.append('circle').attr('r', outerRadius);

  // Compute the chord layout (d3-chord returns chords array with .groups).
  const chords = layout(matrix);

  const group = svg
    .selectAll('.group')
    .data(chords.groups)
    .enter()
    .append('g')
    .attr('class', 'group')
    .on('mouseover', (_event, d) => {
      chordSel.classed(
        'fade',
        p => p.source.index !== d.index && p.target.index !== d.index,
      );
    });

  // Add a mouseover title.
  group.append('title').text(d => `${nodes[d.index]}: ${f(d.value)}`);

  // Add the group arc.
  const groupPath = group
    .append('path')
    .attr('id', d => `group${d.index}`)
    .attr('d', arc)
    .style('fill', d => colorFn(nodes[d.index], sliceId));

  // Add a text label.
  const groupText = group.append('text').attr('x', 6).attr('dy', 15);

  groupText
    .append('textPath')
    .attr('xlink:href', d => `#group${d.index}`)
    .text(d => nodes[d.index]);
  // Remove the labels that don't fit. :(
  groupText
    .filter(function filter(d, i) {
      const pathNode = groupPath.nodes()[i] as SVGPathElement;
      // jsdom does not implement SVGGeometryElement.getTotalLength
      if (typeof pathNode?.getTotalLength !== 'function') {
        return false;
      }
      return pathNode.getTotalLength() / 2 - 16 < this.getComputedTextLength();
    })
    .remove();

  // Add the chords.
  chordSel = svg
    .selectAll('.chord')
    .data(chords)
    .enter()
    .append('path')
    .attr('class', 'chord')
    .on('mouseover', (_event, d) => {
      chordSel.classed('fade', p => p !== d);
    })
    .style('fill', d => colorFn(nodes[d.source.index], sliceId))
    .attr('d', ribbonPath);

  // Add an elaborate mouseover title for each chord.
  chordSel
    .append('title')
    .text(
      d =>
        `${nodes[d.source.index]} \u2192 ${nodes[d.target.index]}: ${f(
          d.target.value,
        )}\n${nodes[d.target.index]} \u2192 ${nodes[d.source.index]}: ${f(
          d.source.value,
        )}`,
    );
}

Chord.displayName = 'Chord';

export default Chord;
