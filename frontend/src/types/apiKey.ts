export interface ApiKeyInfo {
  api_key_id: number;
  tenant_id: number;
  masked_key: string;
  created_at: string | null;
  last_used_at: string | null;
  is_active: boolean;
}

export interface ApiKeyGenerated {
  api_key_id: number;
  tenant_id: number;
  api_key: string;
  masked_key: string;
  created_at: string;
  message: string;
}
