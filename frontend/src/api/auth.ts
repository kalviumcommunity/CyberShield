import api from './axios';
import type { LoginPayload, RegisterPayload, TokenResponse, User } from '../types';

export const login = async (payload: LoginPayload): Promise<TokenResponse> => {
  const { data } = await api.post<TokenResponse>('/auth/login', payload);
  return data;
};

export const register = async (payload: RegisterPayload): Promise<User> => {
  const { data } = await api.post<User>('/auth/register', payload);
  return data;
};

export const getMe = async (): Promise<User> => {
  const { data } = await api.get<User>('/auth/me');
  return data;
};
