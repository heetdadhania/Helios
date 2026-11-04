/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ENABLE_DB_CONNECTION?: string;
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_ADMIN_PASSWORD?: string;
  readonly VITE_TEST_ACCOUNT_PASSWORD?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
