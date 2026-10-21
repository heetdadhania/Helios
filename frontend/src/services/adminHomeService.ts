import apiClient from '@/services/api';
import { AdminHomeResponse } from '@/types/adminHome';

export const adminHomeService = {
  getAdminHome: async (): Promise<AdminHomeResponse> => {
    const response = await apiClient.get<AdminHomeResponse>('/oversight/home');
    return response.data;
  },
};
