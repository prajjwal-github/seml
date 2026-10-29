/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Public URL of the FastAPI backend, (empty = same origin via the Vite proxy) */
  readonly VITE_API_URL?: string;
  /** Optional explicit WebSocket URL,  */
  readonly VITE_WS_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
