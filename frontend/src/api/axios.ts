import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
});

// Attach JWT token on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('cybershield_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401, clear auth and redirect to login
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('cybershield_token');
      localStorage.removeItem('cybershield_user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
