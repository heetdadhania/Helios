import api from '@/services/api';
import {
  ProfileData,
  ProfileUpdateEmailPayload,
  ProfileUpdateMePayload,
  ProfileUpdateOrganizationPayload,
} from '@/types/profile';

export const profileService = {
  async getProfile(): Promise<ProfileData> {
    const response = await api.get<ProfileData>('/profile/me');
    return response.data;
  },

  async updateProfile(data: ProfileUpdateMePayload): Promise<ProfileData> {
    const response = await api.patch<ProfileData>('/profile/me', data);
    return response.data;
  },

  async updateEmail(data: ProfileUpdateEmailPayload): Promise<ProfileData> {
    const response = await api.patch<ProfileData>('/profile/me/email', data);
    return response.data;
  },

  async updateOrganization(data: ProfileUpdateOrganizationPayload): Promise<ProfileData> {
    const response = await api.patch<ProfileData>('/profile/me/organization', data);
    return response.data;
  },
};
