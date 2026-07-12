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
import type {
  ConnectDragSource,
  ConnectDragPreview,
  ConnectDropTarget,
} from 'react-dnd';
import { LayoutItem, ComponentType } from 'src/dashboard/types';

// note: the 'type' hook is not useful for us as dropping is contingent on other properties
export const DRAG_DROPPABLE_TYPE = 'DRAG_DROPPABLE';

export interface DragDroppableProps {
  component: LayoutItem;
  parentComponent?: LayoutItem;
  index: number;
  depth: number;
  disableDragDrop: boolean;
  orientation?: 'row' | 'column';
  isDraggingOverShallow?: boolean;
  onDrop?: (dropResult: DropResult) => void;
  onHover?: () => void;
  dropToChild?: boolean | ((draggingItem: DragItem) => boolean);
}

export interface DragItem {
  type: ComponentType;
  id: string;
  meta: LayoutItem['meta'];
  index: number;
  parentId?: string;
  parentType?: ComponentType;
}

export interface DropResult {
  source: {
    id: string;
    type: ComponentType;
    index: number;
  };
  dragging: {
    id: string;
    type: ComponentType;
    meta: LayoutItem['meta'];
  };
  destination?: {
    id: string;
    type: ComponentType;
    index: number;
  };
  position?: string;
}

export interface DragStateProps {
  dragSourceRef: ConnectDragSource;
  dragPreviewRef: ConnectDragPreview;
  isDragging: boolean;
  dragComponentType?: ComponentType;
  dragComponentId?: string;
}

export interface DropStateProps {
  droppableRef: ConnectDropTarget;
  isDraggingOver: boolean;
  isDraggingOverShallow: boolean;
}

export interface DragDroppableComponent {
  mounted: boolean;
  ref?: HTMLElement | null;
  props: DragDroppableProps;
  setState: (stateUpdate: () => { dropIndicator: string | null }) => void;
}

export function buildDragItem(props: DragDroppableProps): DragItem {
  const { component, index, parentComponent } = props;
  return {
    type: component.type,
    id: component.id,
    meta: component.meta,
    index,
    parentId: parentComponent?.id,
    parentType: parentComponent?.type,
  };
}
