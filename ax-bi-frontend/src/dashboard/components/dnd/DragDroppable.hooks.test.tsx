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
import { render, screen } from 'spec/helpers/testing-library';
import newComponentFactory from 'src/dashboard/util/newComponentFactory';
import {
  CHART_TYPE,
  ROW_TYPE,
} from 'src/dashboard/util/componentTypes';
import {
  DragDroppable,
  Draggable,
  Droppable,
} from 'src/dashboard/components/dnd/DragDroppable';
import { buildDragItem, DRAG_DROPPABLE_TYPE } from './dragDroppableConfig';

const chart = newComponentFactory(CHART_TYPE);
const row = newComponentFactory(ROW_TYPE);

const baseProps = {
  component: chart,
  parentComponent: row,
  editMode: true,
  depth: 1,
  index: 0,
  disableDragDrop: false,
};

test('DragDroppable mounts under DndProvider and exposes dragSourceRef in edit mode', () => {
  const child = jest.fn((provided: Record<string, unknown>) => (
    <div data-test="child" {...provided}>
      content
    </div>
  ));

  render(
    <DragDroppable {...baseProps}>{child}</DragDroppable>,
    { useDnd: true },
  );

  expect(screen.getByTestId('dragdroppable-object')).toBeInTheDocument();
  expect(child).toHaveBeenCalledWith(
    expect.objectContaining({
      'data-test': 'dragdroppable-content',
      dragSourceRef: expect.any(Function),
    }),
  );
});

test('Draggable and Droppable variants mount under DndProvider', () => {
  render(
    <>
      <Draggable {...baseProps}>
        {() => <div data-test="draggable-child">drag</div>}
      </Draggable>
      <Droppable {...baseProps}>
        {() => <div data-test="droppable-child">drop</div>}
      </Droppable>
    </>,
    { useDnd: true },
  );

  expect(screen.getByTestId('draggable-child')).toBeInTheDocument();
  expect(screen.getByTestId('droppable-child')).toBeInTheDocument();
});

test('buildDragItem serializes component identity for the drag payload', () => {
  const item = buildDragItem({
    component: chart,
    parentComponent: row,
    index: 2,
    depth: 1,
    disableDragDrop: false,
  });

  expect(item).toEqual({
    type: chart.type,
    id: chart.id,
    meta: chart.meta,
    index: 2,
    parentId: row.id,
    parentType: row.type,
  });
  expect(DRAG_DROPPABLE_TYPE).toBe('DRAG_DROPPABLE');
});
