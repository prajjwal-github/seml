export type UserRole = 'OPERATOR' | 'APPROVER' | 'ADMIN' | 'AUDITOR';

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  org_id?: string;
  is_active: boolean;
  last_login?: string;
  created_at: string;
}

export type DeviceCategory =
  | 'LAPTOP'
  | 'DESKTOP'
  | 'WORKSTATION'
  | 'SERVER'
  | 'PHONE'
  | 'TABLET'
  | 'ALL_IN_ONE'
  | 'SMART_TV'
  | 'SINGLE_BOARD_COMPUTER'
  | 'EXTERNAL_DRIVE'
  | 'USB_FLASH'
  | 'SD_CARD'
  | 'NETWORK_DEVICE'
  | 'OTHER';

export type DeviceStatus =
  | 'DISCOVERED'
  | 'INVENTORY'
  | 'PENDING_WIPE'
  | 'WIPING'
  | 'VERIFIED'
  | 'CERTIFIED'
  | 'FAILED'
  | 'RECYCLED';

export interface StorageVolume {
  id: string;
  device_id: string;
  name: string;
  media_type: string;
  size_bytes: number;
  serial_number?: string;
  model?: string;
  bus_type?: string;
  is_removable: boolean;
  is_system: boolean;
  partition_table?: string;
  mount_point?: string;
  encryption_status?: string;
  hidden_areas?: {
    hpa_present?: boolean;
    dco_present?: boolean;
    over_provisioning_percent?: number;
    remapped_sectors?: number;
  };
  smart_attributes?: Record<string, any>;
  created_at: string;
}

export interface Device {
  id: string;
  category: DeviceCategory;
  manufacturer: string;
  model: string;
  product_name?: string;
  serial_number: string;
  uuid?: string;
  hostname?: string;
  os_family?: string;
  os_name?: string;
  os_version?: string;
  os_build?: string;
  cpu_arch?: string;
  bios_vendor?: string;
  bios_version?: string;
  boot_mode?: string;
  detected_by?: string;
  detection_confidence?: number;
  status: DeviceStatus;
  agent_id?: string;
  is_online?: boolean;
  volumes?: StorageVolume[];
  created_at: string;
  updated_at: string;
}

export type WipeMethod =
  | 'NIST_800_88_CLEAR'
  | 'NIST_800_88_PURGE'
  | 'CRYPTO_ERASE'
  | 'SIMULATED_OVERWRITE_3PASS';

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type RequestStatus =
  | 'DRAFT'
  | 'PENDING_APPROVAL'
  | 'APPROVED'
  | 'QUEUED'
  | 'RUNNING'
  | 'VERIFYING'
  | 'COMPLETED'
  | 'REJECTED'
  | 'EXPIRED'
  | 'FAILED'
  | 'CANCELLED';

export interface WipeRequest {
  id: string;
  device_id: string;
  requested_by: string;
  reason: string;
  method: WipeMethod;
  nist_category: string;
  volume_ids: string[];
  risk_level: RiskLevel;
  status: RequestStatus;
  expires_at: string;
  decided_at?: string;
  created_at: string;
  updated_at: string;
  device_name?: string;
  requester_name?: string;
}

export interface Approval {
  id: string;
  request_id: string;
  approver_id: string;
  decision: 'APPROVED' | 'REJECTED';
  comment?: string;
  request_fingerprint: string;
  created_at: string;
}

export interface WipeJob {
  id: string;
  request_id: string;
  approval_id: string;
  status: RequestStatus;
  progress: number;
  current_pass: number;
  total_passes: number;
  mode: string;
  started_at?: string;
  finished_at?: string;
  result?: {
    verified?: boolean;
    verification_sample_percent?: number;
    hidden_area_sanitized?: boolean;
    duration_seconds?: number;
    passes_completed?: number;
  };
  created_at: string;
  updated_at: string;
  device_model?: string;
  method?: string;
}

export interface Certificate {
  id: string;
  certificate_id: string;
  job_id: string;
  payload: Record<string, any>;
  payload_sha256: string;
  signature: string;
  public_key_id: string;
  pdf_path: string;
  issued_at: string;
  revoked_at?: string;
  revocation_reason?: string;
  device_model?: string;
  method?: string;
}

export interface AuditLog {
  seq: number;
  id: string;
  timestamp: string;
  ts?: string;
  actor_id?: string;
  actor_email?: string;
  actor_name?: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  ip_address?: string;
  details?: Record<string, any>;
  prev_hash: string;
  hash: string;
}

export interface ReportsSummary {
  total_wiped?: number;
  wiped_devices?: number;
  total_devices?: number;
  wiping_now?: number;
  active_jobs?: number;
  pending_approvals?: number;
  certificates_count?: number;
  certificates_issued?: number;
  by_category?: Record<string, number>;
  devices_by_category?: Record<string, number>;
  by_method?: Record<string, number>;
  wipes_by_method?: Record<string, number>;
  average_turnaround_minutes?: number;
  avg_approval_turnaround_hours?: number;
  audit_chain_valid?: boolean;
  recent_activity?: any[];
}

