/**
 * WebSocket manager with reconnection backoff, channel subscriptions, and event bus.
 */

import { wsUrl as baseWsUrl } from './config';

type Listener = (data: any) => void;

class WebSocketClient {
  private socket: WebSocket | null = null;
  private listeners: Map<string, Set<Listener>> = new Map();
  private reconnectTimeout: number | null = null;
  private isConnecting = false;
  private reconnectAttempts = 0;
  private channels: Set<string> = new Set(['global']);

  connect() {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isConnecting = true;
    const token = localStorage.getItem('securewipe_access_token');
    const tokenParam = token ? `?token=${encodeURIComponent(token)}` : '';
    const wsUrl = `${baseWsUrl()}${tokenParam}`;

    try {
      this.socket = new WebSocket(wsUrl);

      this.socket.onopen = () => {
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.emit('connection.status', { connected: true });

        // Resubscribe to channels
        for (const ch of this.channels) {
          if (ch !== 'global') {
            this.send({ action: 'subscribe', channel: ch });
          }
        }
      };

      this.socket.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          const type = msg.type || 'message';
          this.emit(type, msg);
          this.emit('*', msg);
        } catch {
          // Non-JSON message
        }
      };

      this.socket.onclose = () => {
        this.isConnecting = false;
        this.emit('connection.status', { connected: false });
        this.scheduleReconnect();
      };

      this.socket.onerror = () => {
        this.isConnecting = false;
      };
    } catch {
      this.isConnecting = false;
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimeout) return;
    const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 10000);
    this.reconnectAttempts++;
    this.reconnectTimeout = window.setTimeout(() => {
      this.reconnectTimeout = null;
      this.connect();
    }, delay);
  }

  send(data: any) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(typeof data === 'string' ? data : JSON.stringify(data));
    }
  }

  subscribe(channel: string) {
    this.channels.add(channel);
    this.send({ action: 'subscribe', channel });
  }

  on(event: string, callback: Listener) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
    return () => this.off(event, callback);
  }

  off(event: string, callback: Listener) {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.delete(callback);
    }
  }

  private emit(event: string, data: any) {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.forEach((cb) => {
        try {
          cb(data);
        } catch (e) {
          console.error('WS listener error', e);
        }
      });
    }
  }
}

export const wsClient = new WebSocketClient();
