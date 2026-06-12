export interface ServiceConfig {
  port: number;
  serviceName: string;
  postgresUrl?: string;
  mongoUrl?: string;
  redisUrl?: string;
  kafkaBrokers?: string[];
  jwtSecret?: string;
}

export interface PaginationQuery {
  page: number;
  limit: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

export interface AuditEntry {
  userId: string;
  action: string;
  resourceType: string;
  resourceId: string;
  details?: Record<string, unknown>;
  ipAddress?: string;
  userAgent?: string;
  timestamp: Date;
}

export enum UserType {
  CITIZEN = 'citizen',
  OFFICER = 'officer',
  INSPECTOR = 'inspector',
  ADMIN = 'admin',
  JUDGE = 'judge',
  MODERATOR = 'moderator',
}

export enum FirStatus {
  REGISTERED = 'registered',
  UNDER_REVIEW = 'under_review',
  INVESTIGATION = 'investigation',
  COURT_REFERRED = 'court_referred',
  RESOLVED = 'resolved',
  CLOSED = 'closed',
  FALSE_REPORT = 'false_report',
}

export enum EvidenceStatus {
  TEMPORARY = 'temporary',
  UNDER_REVIEW = 'under_review',
  VERIFIED_PERMANENT = 'verified_permanent',
  REJECTED = 'rejected',
}

export enum Severity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}
