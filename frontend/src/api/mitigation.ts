import api from './axios';
import type {
  MitigationAnswerRequest,
  MitigationAnswerResponse,
  MitigationSearchRequest,
  MitigationSearchResponse,
} from '../types';

export const searchMitigations = async (
  payload: MitigationSearchRequest
): Promise<MitigationSearchResponse> => {
  const { data } = await api.post<MitigationSearchResponse>('/mitigation/search', payload);
  return data;
};

export const getMitigationAnswer = async (
  payload: MitigationAnswerRequest
): Promise<MitigationAnswerResponse> => {
  const { data } = await api.post<MitigationAnswerResponse>('/mitigation/answer', payload);
  return data;
};
