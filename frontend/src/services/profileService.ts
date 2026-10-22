import api from '@/services/api';
import { ProfileData } from '@/types/profile';

export const profileService = {
  async getProfile(): Promise<ProfileData> {
    const response = await api.get<ProfileData>('/profile/me');
    return response.data;
  },
};
