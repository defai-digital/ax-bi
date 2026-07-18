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

declare module '*.png' {
  const value: string;
  export default value;
}

declare module '*.jpg' {
  const value: string;
  export default value;
}

// d3-chord ships no bundled type declarations and @types/d3-chord is not
// installed, so declare the subset of the API this plugin uses.
declare module 'd3-chord' {
  export interface ChordGroup {
    startAngle: number;
    endAngle: number;
    value: number;
    index: number;
  }

  export interface ChordSubgroup extends ChordGroup {
    subindex: number;
  }

  export interface Chord {
    source: ChordSubgroup;
    target: ChordSubgroup;
  }

  export interface Chords extends Array<Chord> {
    groups: ChordGroup[];
  }

  export interface ChordLayout {
    (matrix: number[][]): Chords;
    padAngle(): number;
    padAngle(angle: number): this;
    sortGroups(): ((a: number, b: number) => number) | null;
    sortGroups(compare: ((a: number, b: number) => number) | null): this;
    sortSubgroups(): ((a: number, b: number) => number) | null;
    sortSubgroups(compare: ((a: number, b: number) => number) | null): this;
    sortChords(): ((a: number, b: number) => number) | null;
    sortChords(compare: ((a: number, b: number) => number) | null): this;
  }

  export function chord(): ChordLayout;

  export interface Ribbon {
    source: ChordSubgroup;
    target: ChordSubgroup;
  }

  export interface RibbonGenerator<This, Datum> {
    (this: This, d: Datum, ...args: any[]): string | null;
    context(): CanvasRenderingContext2D | null;
    context(context: CanvasRenderingContext2D | null): this;
    source(): (this: This, d: Datum, ...args: any[]) => any;
    source(source: (this: This, d: Datum, ...args: any[]) => any): this;
    target(): (this: This, d: Datum, ...args: any[]) => any;
    target(target: (this: This, d: Datum, ...args: any[]) => any): this;
    radius(): (this: This, d: Datum, ...args: any[]) => number;
    radius(radius: number): this;
    radius(radius: (this: This, d: Datum, ...args: any[]) => number): this;
    startAngle(): (this: This, d: Datum, ...args: any[]) => number;
    startAngle(angle: number): this;
    startAngle(angle: (this: This, d: Datum, ...args: any[]) => number): this;
    endAngle(): (this: This, d: Datum, ...args: any[]) => number;
    endAngle(angle: number): this;
    endAngle(angle: (this: This, d: Datum, ...args: any[]) => number): this;
    padAngle(): (this: This, d: Datum, ...args: any[]) => number;
    padAngle(angle: number): this;
    padAngle(angle: (this: This, d: Datum, ...args: any[]) => number): this;
  }

  export function ribbon(): RibbonGenerator<any, Ribbon>;
}
