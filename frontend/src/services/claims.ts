import api from "./api";

export interface Claim {
  claim_id: string;
  claim_type: string;
  status: string;
  amount: number;
  description: string;
  policy_number?: string;
  incident_date?: string;
  submitted_at: string;
  created_at?: string;
  resolved_at?: string;
  fraud_score?: number;
  documents?: string[];
  user_id?: string;
}

export interface CreateClaimRequest {
  claim_type: string;
  amount: number;
  description: string;
  policy_number?: string;
  incident_date?: string;
  [key: string]: unknown;
}

export interface ClaimListResponse {
  items: Claim[];
  total: number;
  page: number;
  size: number;
}

export const createClaim = async (data: CreateClaimRequest): Promise<Claim> => {
  const response = await api.post<Claim>("/api/claims", data);
  return response.data;
};

export const getClaim = async (claimId: string): Promise<Claim> => {
  const response = await api.get<Claim>(`/api/claims/${claimId}`);
  return response.data;
};

export const listClaims = async (params?: {
  status?: string;
  claim_type?: string;
  page?: number;
  page_size?: number;
  size?: number;
}): Promise<ClaimListResponse> => {
  const response = await api.get<ClaimListResponse>("/api/claims", { params });
  return response.data;
};

export const submitClaim = async (claimId: string): Promise<Claim> => {
  const response = await api.post<Claim>(`/api/claims/${claimId}/submit`);
  return response.data;
};

export const approveClaim = async (
  claimId: string,
  settlementAmount: number,
  notes?: string
): Promise<Claim> => {
  const response = await api.post<Claim>(`/api/claims/${claimId}/approve`, {
    settlement_amount: settlementAmount,
    notes,
  });
  return response.data;
};

export const rejectClaim = async (
  claimId: string,
  reason: string
): Promise<Claim> => {
  const response = await api.post<Claim>(`/api/claims/${claimId}/reject`, {
    reason,
  });
  return response.data;
};

export const settleClaim = async (claimId: string): Promise<Claim> => {
  const response = await api.post<Claim>(`/api/claims/${claimId}/settle`);
  return response.data;
};

export const closeClaim = async (claimId: string): Promise<Claim> => {
  const response = await api.post<Claim>(`/api/claims/${claimId}/close`);
  return response.data;
};

export interface Document {
  document_id: string;
  claim_id: string;
  file_name: string;
  file_size: number;
  document_type: string;
  created_at: string;
}

export const uploadDocument = async (claimId: string, file: File, documentType: string = "supporting_document"): Promise<Document> => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("claim_id", claimId);
  formData.append("document_type", documentType);

  const response = await api.post<Document>("/api/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const getClaimDocuments = async (claimId: string): Promise<Document[]> => {
  const response = await api.get<Document[]>(`/api/documents?claim_id=${claimId}`);
  return response.data;
};
