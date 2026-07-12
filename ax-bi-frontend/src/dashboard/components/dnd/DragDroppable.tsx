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
import { getEmptyImage } from 'react-dnd-html5-backend';
import {
  CSSProperties,
  ReactNode,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';
import {
  ConnectDragPreview,
  ConnectDragSource,
  ConnectDropTarget,
  useDrag,
  useDrop,
} from 'react-dnd';
import cx from 'classnames';
import { css, styled } from '@ax-bi/core/theme';
import { TAB_TYPE } from 'src/dashboard/util/componentTypes';
import {
  buildDragItem,
  DRAG_DROPPABLE_TYPE,
  type DragDroppableComponent,
  type DragDroppableProps as BaseDragDroppableProps,
  type DropResult,
} from './dragDroppableConfig';
import handleHover from './handleHover';
import handleDrop from './handleDrop';
import { DROP_FORBIDDEN } from '../../util/getDropPosition';
import type { ComponentType } from '../../types';

interface DropIndicatorProps {
  className: string;
}

interface ChildProps {
  dragSourceRef?: ConnectDragSource;
  dropIndicatorProps: DropIndicatorProps | null;
  draggingTabOnTab?: boolean;
  'data-test': string;
}

export interface DragDroppableOwnProps extends BaseDragDroppableProps {
  children: (childProps: ChildProps) => ReactNode;
  className?: string | null;
  style?: CSSProperties | null;
  onDropIndicatorChange?: (info: {
    dropIndicator: string | null;
    isDraggingOver: boolean;
    index: number;
  }) => void;
  onDragTab?: (dragComponentId: string | undefined) => void;
  editMode?: boolean;
  useEmptyDragPreview?: boolean;
}

/** Injected by react-dnd hooks; also accepted by the unwrapped test component. */
export interface DragDroppableDndProps {
  isDragging?: boolean;
  isDraggingOver?: boolean;
  isDraggingOverShallow?: boolean;
  dragComponentType?: ComponentType;
  dragComponentId?: string;
  droppableRef?: ConnectDropTarget;
  dragSourceRef?: ConnectDragSource;
  dragPreviewRef?: ConnectDragPreview;
  /** Optional drop indicator override for unit tests */
  dropIndicator?: string | null;
}

type DragDroppableAllProps = DragDroppableOwnProps & DragDroppableDndProps;

type DragMode = 'drag' | 'drop' | 'both';

const DragDroppableStyles = styled.div`
  ${({ theme }) => css`
    position: relative;

    &.dragdroppable--dragging {
      opacity: 0.2;
    }

    &.dragdroppable-row {
      width: 100%;
    }
    /* workaround to avoid a bug in react-dnd where the drag
      preview expands outside of the bounds of the drag source card, see:
      https://github.com/react-dnd/react-dnd/issues/832 */
    &.dragdroppable-column {
      /* for chrome */
      transform: translate3d(0, 0, 0);
      /* for safari */
      backface-visibility: hidden;
    }

    &.dragdroppable-column .resizable-container span div {
      z-index: 10;
    }

    & {
      .drop-indicator {
        display: block;
        background-color: ${theme.colorPrimary};
        position: absolute;
        z-index: 10;
        opacity: 0.3;
        width: 100%;
        height: 100%;
        &.drop-indicator--forbidden {
          background-color: ${theme.colorErrorBg};
        }
      }
    }
  `};
`;

const noopConnector = ((node: unknown) => node) as ConnectDragSource &
  ConnectDropTarget &
  ConnectDragPreview;

/**
 * Presentational drag/drop shell. Accepts connector refs and monitor state as
 * props so unit tests can exercise rendering without live react-dnd hooks.
 */
export function UnwrappedDragDroppable({
  children,
  className = null,
  style = null,
  orientation = 'row',
  disableDragDrop = false,
  editMode = false,
  useEmptyDragPreview = false,
  component,
  index = 0,
  isDragging = false,
  isDraggingOver = false,
  dragComponentType,
  dragComponentId,
  droppableRef = noopConnector,
  dragSourceRef = noopConnector,
  dragPreviewRef = noopConnector,
  dropIndicator = null,
  onDropIndicatorChange,
  onDragTab,
}: DragDroppableAllProps) {
  const prevDropIndicatorRef = useRef(dropIndicator);
  const prevIsDraggingOverRef = useRef(isDraggingOver);
  const prevIndexRef = useRef(index);
  const prevDragComponentIdRef = useRef(dragComponentId);

  const setContainerRef = useCallback(
    (ref: HTMLDivElement | null) => {
      if (useEmptyDragPreview) {
        // Only attach the empty preview while mounted; clear on unmount.
        if (ref) {
          dragPreviewRef(getEmptyImage(), {
            // IE fallback: specify that we'd rather screenshot the node
            // when it already knows it's being dragged so we can hide it with CSS.
            captureDraggingState: true,
          });
        } else {
          dragPreviewRef(null);
        }
      } else {
        dragPreviewRef(ref);
      }
      droppableRef?.(ref);
    },
    [dragPreviewRef, droppableRef, useEmptyDragPreview],
  );

  useEffect(() => {
    const isTabsType = component.type === TAB_TYPE;
    const validStateChange =
      dropIndicator !== prevDropIndicatorRef.current ||
      isDraggingOver !== prevIsDraggingOverRef.current ||
      index !== prevIndexRef.current;

    if (onDropIndicatorChange && isTabsType && validStateChange) {
      onDropIndicatorChange({ dropIndicator, isDraggingOver, index });
    }

    prevDropIndicatorRef.current = dropIndicator;
    prevIsDraggingOverRef.current = isDraggingOver;
    prevIndexRef.current = index;
  }, [
    component.type,
    dropIndicator,
    index,
    isDraggingOver,
    onDropIndicatorChange,
  ]);

  useEffect(() => {
    if (dragComponentId !== prevDragComponentIdRef.current) {
      const timeoutId = window.setTimeout(() => {
        /**
         * This timeout ensures the dragSourceRef and dragPreviewRef are set
         * before the component is removed in Tabs. Otherwise react-dnd
         * will not render the drag preview.
         */
        onDragTab?.(dragComponentId);
      });
      prevDragComponentIdRef.current = dragComponentId;
      return () => window.clearTimeout(timeoutId);
    }
    return undefined;
  }, [dragComponentId, onDragTab]);

  const dropIndicatorProps: DropIndicatorProps | null =
    isDraggingOver && dropIndicator && !disableDragDrop
      ? {
          className: cx(
            'drop-indicator',
            dropIndicator === DROP_FORBIDDEN && 'drop-indicator--forbidden',
          ),
        }
      : null;

  const draggingTabOnTab =
    component.type === TAB_TYPE && dragComponentType === TAB_TYPE;

  const childProps: ChildProps = editMode
    ? {
        dragSourceRef,
        dropIndicatorProps,
        draggingTabOnTab,
        'data-test': 'dragdroppable-content',
      }
    : {
        dropIndicatorProps: null,
        'data-test': 'dragdroppable-content',
      };

  return (
    <DragDroppableStyles
      style={style ?? undefined}
      ref={setContainerRef}
      data-test="dragdroppable-object"
      className={cx(
        'dragdroppable',
        editMode && 'dragdroppable--edit-mode',
        orientation === 'row' && 'dragdroppable-row',
        orientation === 'column' && 'dragdroppable-column',
        isDragging && 'dragdroppable--dragging',
        className,
      )}
    >
      {children(childProps)}
    </DragDroppableStyles>
  );
}

function DragDroppableWithMode({
  mode,
  ...props
}: DragDroppableOwnProps & { mode: DragMode }) {
  const enableDrag = mode === 'drag' || mode === 'both';
  const enableDrop = mode === 'drop' || mode === 'both';
  const [dropIndicator, setDropIndicator] = useState<string | null>(null);

  const propsRef = useRef(props);
  propsRef.current = props;

  const mountedRef = useRef(true);
  const elementRef = useRef<HTMLElement | null>(null);
  const shallowOverRef = useRef(false);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // Stable facade so throttled hover/drop handlers see current props/DOM/state.
  const componentFacadeRef = useRef<DragDroppableComponent | null>(null);
  if (!componentFacadeRef.current) {
    componentFacadeRef.current = {
      get mounted() {
        return mountedRef.current;
      },
      get ref() {
        return elementRef.current;
      },
      set ref(value: HTMLElement | null | undefined) {
        elementRef.current = value ?? null;
      },
      get props() {
        return {
          ...propsRef.current,
          isDraggingOverShallow: shallowOverRef.current,
        };
      },
      setState(stateUpdate: () => { dropIndicator: string | null }) {
        setDropIndicator(stateUpdate().dropIndicator);
      },
    };
  }

  const [{ isDragging, dragComponentType, dragComponentId }, drag, preview] =
    useDrag(
      () => ({
        type: DRAG_DROPPABLE_TYPE,
        item: () => buildDragItem(propsRef.current),
        canDrag: () =>
          enableDrag && !(propsRef.current.disableDragDrop ?? false),
        collect: monitor => ({
          isDragging: enableDrag && monitor.isDragging(),
          dragComponentType: monitor.getItem()?.type as
            ComponentType | undefined,
          dragComponentId: monitor.getItem()?.id as string | undefined,
        }),
      }),
      [enableDrag],
    );

  const [{ isDraggingOver, isDraggingOverShallow }, drop] = useDrop(
    () => ({
      accept: DRAG_DROPPABLE_TYPE,
      canDrop: () => enableDrop && !(propsRef.current.disableDragDrop ?? false),
      hover: (_item, monitor) => {
        if (!enableDrop || !componentFacadeRef.current) {
          return;
        }
        handleHover(propsRef.current, monitor, componentFacadeRef.current);
      },
      drop: (_item, monitor): DropResult | undefined => {
        if (!enableDrop || !componentFacadeRef.current) {
          return undefined;
        }
        const dropResult = monitor.getDropResult() as DropResult | null;
        if (
          (!dropResult || !dropResult.destination) &&
          componentFacadeRef.current.mounted
        ) {
          return handleDrop(
            propsRef.current,
            monitor,
            componentFacadeRef.current,
          );
        }
        return undefined;
      },
      collect: monitor => {
        const nextShallow = enableDrop && monitor.isOver({ shallow: true });
        shallowOverRef.current = nextShallow;
        return {
          isDraggingOver: enableDrop && monitor.isOver(),
          isDraggingOverShallow: nextShallow,
        };
      },
    }),
    [enableDrop],
  );

  const droppableRef = useCallback(
    (node: HTMLElement | null) => {
      elementRef.current = node;
      if (enableDrop) {
        drop(node);
      }
    },
    [drop, enableDrop],
  ) as ConnectDropTarget;

  const dragPreviewRef = useCallback(
    (
      node: Parameters<ConnectDragPreview>[0],
      options?: Parameters<ConnectDragPreview>[1],
    ) => {
      if (enableDrag) {
        preview(node, options);
      }
    },
    [enableDrag, preview],
  ) as ConnectDragPreview;

  const dragSourceRef = (
    enableDrag ? drag : noopConnector
  ) as ConnectDragSource;

  // Clear drop indicator when drag leaves this target.
  useEffect(() => {
    if (!isDraggingOver && dropIndicator !== null) {
      setDropIndicator(null);
    }
  }, [dropIndicator, isDraggingOver]);

  return (
    <UnwrappedDragDroppable
      {...props}
      isDragging={isDragging}
      isDraggingOver={isDraggingOver}
      isDraggingOverShallow={isDraggingOverShallow}
      dragComponentType={dragComponentType}
      dragComponentId={dragComponentId}
      droppableRef={droppableRef}
      dragSourceRef={dragSourceRef}
      dragPreviewRef={dragPreviewRef}
      dropIndicator={dropIndicator}
    />
  );
}

export function Draggable(props: DragDroppableOwnProps) {
  return <DragDroppableWithMode mode="drag" {...props} />;
}

export function Droppable(props: DragDroppableOwnProps) {
  return <DragDroppableWithMode mode="drop" {...props} />;
}

export function DragDroppable(props: DragDroppableOwnProps) {
  return <DragDroppableWithMode mode="both" {...props} />;
}
