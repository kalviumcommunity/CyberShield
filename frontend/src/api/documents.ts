import api from './axios';
import type {
  Document,
  DocumentChunk,
  DocumentEmbedResponse,
  DocumentProcessResponse,
  DocumentType,
  DocumentUploadResponse,
} from '../types';

export const getDocuments = async (
  skip = 0,
  limit = 100,
  document_type?: DocumentType
): Promise<Document[]> => {
  const params: Record<string, unknown> = { skip, limit };
  if (document_type) params.document_type = document_type;
  const { data } = await api.get<Document[]>('/documents', { params });
  return data;
};

export const getDocument = async (id: number): Promise<Document> => {
  const { data } = await api.get<Document>(`/documents/${id}`);
  return data;
};

export const getDocumentChunks = async (id: number): Promise<DocumentChunk[]> => {
  const { data } = await api.get<DocumentChunk[]>(`/documents/${id}/chunks`);
  return data;
};

export const uploadDocument = async (
  file: File,
  document_type: DocumentType,
  title?: string
): Promise<DocumentUploadResponse> => {
  const form = new FormData();
  form.append('file', file);
  form.append('document_type', document_type);
  if (title) form.append('title', title);
  const { data } = await api.post<DocumentUploadResponse>('/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export const processDocument = async (
  id: number,
  force = false
): Promise<DocumentProcessResponse> => {
  const { data } = await api.post<DocumentProcessResponse>(`/documents/${id}/process`, null, {
    params: { force },
  });
  return data;
};

export const embedDocument = async (
  id: number,
  force = false
): Promise<DocumentEmbedResponse> => {
  const { data } = await api.post<DocumentEmbedResponse>(`/documents/${id}/embed`, null, {
    params: { force },
  });
  return data;
};
