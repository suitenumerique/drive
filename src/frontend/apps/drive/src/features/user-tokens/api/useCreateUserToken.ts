import { useMutation } from '@tanstack/react-query';

import { APIError } from '@/features/api/APIError';

import { NewUserToken } from '../types';
import {fetchAPI} from "@/features/api/fetchApi";

export const createUserToken = async (): Promise<NewUserToken> => {
  const response = await fetchAPI(`user-tokens/`, {
    method: 'POST',
    // The backend test indicates no data is sent for creation, so body is an empty object
    body: JSON.stringify({}),
  });

  if (!response.ok) {
    throw new APIError(
      response.status,
      response.statusText,
    );
  }

  return response.json() as Promise<NewUserToken>;
};

export function useCreateUserToken() {
  return useMutation<NewUserToken, APIError>({
    mutationFn: createUserToken,
  });
}
