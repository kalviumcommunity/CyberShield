import api from './axios';
import type { SearchRebuildResponse, SearchResultItem } from '../types';

export const semanticSearch = async (
  q: string,
  top_k = 5
): Promise<SearchResultItem[]> => {
  const { data } = await api.get<SearchResultItem[]>('/search', {
    params: { q, top_k },
  });
  return data;
};

export const rebuildIndex = async (
  auto_embed = false
): Promise<SearchRebuildResponse> => {
  const { data } = await api.post<SearchRebuildResponse>('/search/rebuild', null, {
    params: { auto_embed },
  });
  return data;
};
