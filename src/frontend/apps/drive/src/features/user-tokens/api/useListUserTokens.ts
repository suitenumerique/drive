import { useQuery } from '@tanstack/react-query';

import { APIError } from '@/features/api/APIError';
import {fetchAPI} from "@/features/api/fetchApi";

import { UserToken } from '../types';

export const listUserTokens = async (): Promise<UserToken[]> => {
  const response = await fetchAPI(`user-tokens/`);

  if (!response.ok) {
    throw new APIError(
        response.status,
        response.statusText,
    );
  }

  return response.json() as Promise<UserToken[]>;
};

export function useListUserTokens() {
  return useQuery<UserToken[], APIError>({
    queryKey: ['userTokens'],
    queryFn: listUserTokens,
  });
}
