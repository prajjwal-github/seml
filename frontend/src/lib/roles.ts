import { UserRole } from '../types';

export interface RoleInfo {
  role: UserRole;
  title: string;
  subtitle: string;
  description: string;
  email: string;
}

/** The three platform roles, in the order the certificate workflow runs. */
export const ROLES: RoleInfo[] = [
  {
    role: 'ADMIN',
    title: 'Admin',
    subtitle: 'Asset registry',
    description: 'Adds and manages every office device (laptops, tablets, phones, drives).',
    email: 'admin@securewipe.local',
  },
  {
    role: 'OPERATOR',
    title: 'Operator',
    subtitle: 'Device owner / user',
    description: 'Picks a device and submits a request for its data-wipe certificate.',
    email: 'operator@securewipe.local',
  },
  {
    role: 'APPROVER',
    title: 'Approver',
    subtitle: 'Certifying authority',
    description: 'Reviews requests and approves or rejects certificate generation.',
    email: 'approver@securewipe.local',
  },
];

export const roleInfo = (role?: UserRole): RoleInfo | undefined => ROLES.find((r) => r.role === role);

/** Human label for a request / device certificate lifecycle status. */
export function certStatusLabel(status?: string): string {
  switch (status) {
    case undefined:
    case 'NONE':
      return 'Registered';
    case 'PENDING_APPROVAL':
      return 'Awaiting approval';
    case 'APPROVED':
    case 'QUEUED':
      return 'Approved, starting wipe';
    case 'RUNNING':
      return 'Wiping data';
    case 'VERIFYING':
      return 'Verifying wipe';
    case 'COMPLETED':
      return 'Certificate ready';
    case 'REJECTED':
      return 'Rejected';
    case 'CANCELLED':
      return 'Withdrawn';
    case 'FAILED':
      return 'Wipe failed';
    case 'EXPIRED':
      return 'Expired';
    default:
      return status.replace(/_/g, ' ');
  }
}

/** Statuses during which a device has an open certificate request. */
export const ACTIVE_STATUSES = ['PENDING_APPROVAL', 'APPROVED', 'QUEUED', 'RUNNING', 'VERIFYING'];

/** "NIST_800_88_PURGE" -> "NIST 800-88 Purge" */
export function formatMethod(method?: string): string {
  if (!method) return '';
  const m = method.match(/^NIST_800_88_(\w+)$/);
  if (m) return `NIST 800-88 ${m[1].charAt(0)}${m[1].slice(1).toLowerCase()}`;
  return method.replace(/_/g, ' ');
}
