/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Public URL of the FastAPI backend, e.g. https://securewipe-api.onrender.com (empty = same origin / Vite proxy) */
  readonly VITE_API_URL?: string;
  /** Optional explicit WebSocket URL, e.g. wss://securewipe-api.onrender.com/ws */
  readonly VITE_WS_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
