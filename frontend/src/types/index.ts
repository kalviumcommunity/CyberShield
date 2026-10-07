// ============================================================
// TypeScript interfaces mirroring backend Pydantic schemas
// ============================================================

export type UserRole = 'admin' | 'analyst';

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  name: string;
  email: string;
  password: string;
  role: UserRole;
}

// ---- Documents ----

export type DocumentType =
  | 'threat_intelligence'
  | 'incident_runbook'
  | 'vulnerability_advisory';

export interface Document {
  id: number;
  title: string;
  document_type: DocumentType;
  file_name: string;
  file_path: string;
  content: string | null;
  extracted_text_length: number;
  uploaded_by: number;
  created_at: string;
}

export interface DocumentUploadResponse extends Document {
  document_id: number;
  filename: string;
  upload_status: string;
}

export interface DocumentProcessResponse {
  document_id: number;
  chunks_created: number;
  processing_status: string;
  message: string;
}

export interface DocumentEmbedResponse {
  document_id: number;
  chunks_embedded: number;
  embedding_dimension: number;
  status: string;
  message: string;
}

export interface DocumentChunk {
  id: number;
  document_id: number;
  chunk_index: number;
  content: string;
  embedding: string | null;
}

// ---- Search ----

export interface SearchResultItem {
  chunk_id: number;
  document_id: number;
  document_title: string;
  chunk_content: string;
  similarity_score: number;
  relevance_score: number;
}

export interface SearchRebuildResponse {
  status: string;
  indexed_chunks: number;
  message: string;
}

// ---- Mitigation ----

export type Severity = 'low' | 'medium' | 'high' | 'critical';

export interface MitigationSearchRequest {
  alert: string;
  top_k?: number;
  min_threshold?: number;
  severity?: Severity;
  save_record?: boolean;
}

export interface MitigationResult {
  document_id: number;
  document_title: string;
  document_type: DocumentType;
  chunk_id: number;
  mitigation_text: string;
  relevance_score: number;
  source_file: string;
}

export interface MitigationSearchResponse {
  alert: string;
  results: MitigationResult[];
  total_results: number;
  alert_id: number | null;
}

export interface MitigationAnswerRequest {
  alert: string;
  top_k?: number;
  min_threshold?: number;
  severity?: Severity;
}

export interface MitigationAnswerResponse {
  alert: string;
  answer: string;
  sources: MitigationResult[];
  results: MitigationResult[];
  alert_id: number | null;
}

// ---- Health ----

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  environment: string;
  database: string;
  vector_index: {
    status: string;
    indexed_chunks: number;
  };
  timestamp: string;
  message: string;
}
