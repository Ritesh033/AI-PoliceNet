export interface User {
  id: string;
  registrationId: string;
  email: string | null;
  phone: string | null;
  fullName: string;
  userType: string;
  isVerified: boolean;
  state?: string;
  district?: string;
}

export interface FIR {
  id: string;
  firNumber: string;
  title: string;
  description: string;
  status: FirStatus;
  category?: string;
  severity?: string;
  incidentDate?: string;
  incidentLocation?: string;
  aiRiskScore?: number;
  createdAt: string;
  updatedAt: string;
}

export type FirStatus =
  | 'registered'
  | 'under_review'
  | 'investigation'
  | 'court_referred'
  | 'resolved'
  | 'closed'
  | 'false_report';

export interface Evidence {
  evidenceId: string;
  firId: string;
  fileType: 'video' | 'audio' | 'image' | 'document';
  status: 'temporary' | 'under_review' | 'verified_permanent' | 'rejected';
  reviewDeadline: string;
  createdAt: string;
}

export interface Notification {
  id: string;
  subject: string;
  message: string;
  read: boolean;
  createdAt: string;
}
