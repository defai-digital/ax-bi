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
declare module 'react-ace' {
  import { Component, type CSSProperties } from 'react';

  export interface Annotation {
    row: number;
    column: number;
    type: string;
    text: string;
  }

  export interface Marker {
    startRow: number;
    startCol: number;
    endRow: number;
    endCol: number;
    className: string;
    type: string;
  }

  export interface EditorProps {
    $blockScrolling?: number | boolean;
    $useWorker?: boolean;
    [key: string]: unknown;
  }

  export interface AceEditorCommand {
    name: string;
    bindKey: { win: string; mac: string };
    exec: (editor: AceEditorInstance) => void;
  }

  export interface AceEditorInstance {
    commands: {
      addCommand: (command: AceEditorCommand) => void;
      removeCommand: (name: string) => void;
      exec: (name: string, editor: AceEditorInstance, args?: unknown) => void;
      on: (event: string, callback: (...args: unknown[]) => void) => void;
      off: (event: string, callback: (...args: unknown[]) => void) => void;
    };
    selection: {
      on: (event: string, callback: () => void) => void;
      off: (event: string, callback: () => void) => void;
      setSelectionRange: (range: unknown, reverse?: boolean) => void;
    };
    session: {
      doc: {
        positionToIndex: (pos: { row: number; column: number }) => number;
        getNewLineCharacter: () => string;
      };
      on: (event: string, callback: (...args: unknown[]) => void) => void;
      off: (event: string, callback: (...args: unknown[]) => void) => void;
      setAnnotations: (annotations: Annotation[]) => void;
      clearAnnotations: () => void;
      [key: string]: unknown;
    };
    container: HTMLElement;
    getCursorPosition: () => { row: number; column: number };
    getSelection: () => {
      getRange: () => {
        start: { row: number; column: number };
        end: { row: number; column: number };
      };
    };
    getSelectedText: () => string;
    clearSelection: () => void;
    moveCursorToPosition: (pos: { row: number; column: number }) => void;
    insert: (text: string) => void;
    scrollToLine: (line: number, center?: boolean, animate?: boolean) => void;
    resize: () => void;
    getOption: (name: string) => unknown;
    setOption: (name: string, value: unknown) => void;
    focus: () => void;
    blur: () => void;
    getValue: () => string;
    setValue: (value: string) => void;
    getSession: () => {
      setAnnotations: (annotations: Annotation[]) => void;
      clearAnnotations: () => void;
      [key: string]: unknown;
    };
    renderer: unknown;
    [key: string]: unknown;
  }

  export interface AceEditorProps {
    name?: string;
    style?: CSSProperties;
    className?: string;
    theme?: string;
    mode?: string;
    value?: string;
    defaultValue?: string;
    readOnly?: boolean;
    highlightActiveLine?: boolean;
    showGutter?: boolean;
    showPrintMargin?: boolean;
    minLines?: number;
    maxLines?: number;
    fontSize?: number | string;
    tabSize?: number;
    width?: string;
    height?: string;
    wrapEnabled?: boolean;
    enableBasicAutocompletion?: boolean | string[];
    enableLiveAutocompletion?: boolean | string[];
    enableSnippets?: boolean;
    placeholder?: string;
    annotations?: Annotation[];
    markers?: Marker[];
    editorProps?: EditorProps;
    setOptions?: Record<string, unknown>;
    commands?: Array<{
      name: string;
      bindKey: { win: string; mac: string };
      exec: (editor: AceEditorInstance) => void;
    }>;
    onChange?: (value: string, event?: unknown) => void;
    onFocus?: (event: unknown, editor?: AceEditorInstance) => void;
    onBlur?: (event: unknown, editor?: AceEditorInstance) => void;
    onCursorChange?: (selection: unknown) => void;
    onLoad?: (editor: AceEditorInstance) => void;
    onValidate?: (annotations: Annotation[]) => void;
    ref?: unknown;
    [key: string]: unknown;
  }

  export default class AceEditor extends Component<AceEditorProps> {
    editor: AceEditorInstance;
  }
}
