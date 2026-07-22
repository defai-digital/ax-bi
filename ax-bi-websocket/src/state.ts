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
import WebSocket from 'ws';

export interface SocketInstance {
  ws: WebSocket;
  channel: string;
  pongTs: number;
}

export interface ChannelValue {
  sockets: Array<string>;
}

const SOCKET_ACTIVE_STATES: number[] = [WebSocket.OPEN, WebSocket.CONNECTING];

/**
 * In-memory registries of live WebSocket channels/sockets.
 * Kept in a dedicated module so route handlers (e.g. health) can import
 * counts without creating a circular dependency on index.ts.
 */
export let channels: Record<string, ChannelValue> = {};
export let sockets: Record<string, SocketInstance> = {};

/**
 * Returns whether the socket with the given id is currently active, i.e. it is
 * still registered and its underlying connection is in an active readyState.
 */
export const isSocketActive = (socketId: string): boolean => {
  const socketInstance = sockets[socketId];
  return (
    !!socketInstance &&
    SOCKET_ACTIVE_STATES.includes(socketInstance.ws.readyState)
  );
};

/**
 * Counts the sockets in the global registry that are still active.
 */
export const activeSocketCount = (): number =>
  Object.keys(sockets).filter(isSocketActive).length;

/**
 * Counts the active sockets currently registered on the given channel.
 */
export const activeChannelSocketCount = (channel: string): number =>
  channels[channel]?.sockets.filter(isSocketActive).length ?? 0;

export const resetRegistries = (): void => {
  channels = {};
  sockets = {};
};

export { SOCKET_ACTIVE_STATES };
