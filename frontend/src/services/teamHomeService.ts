import api from './api';
import { TeamHomeResponse } from '@/types/teamHome';

export const teamHomeService = {
  async getTeamHome(): Promise<TeamHomeResponse> {
    const response = await api.get<TeamHomeResponse>('/team/home');
    return response.data;
  },
};
