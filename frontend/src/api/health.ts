import api from './axios';
import type { HealthResponse } from '../types';

export const getHealth = async (): Promise<HealthResponse> => {
  const { data } = await api.get<HealthResponse>('/health');
  return data;
};
