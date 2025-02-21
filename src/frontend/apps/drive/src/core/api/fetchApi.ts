import { logout } from '@/core/auth/Auth';
import { baseApiUrl } from '@/core/conf';

/**
 * Retrieves the CSRF token from the document's cookies.
 *
 * @returns {string|null} The CSRF token if found in the cookies, or null if not present.
 */
function getCSRFToken() {
  return document.cookie
    .split(';')
    .filter((cookie) => cookie.trim().startsWith('csrftoken='))
    .map((cookie) => cookie.split('=')[1])
    .pop();
}

export interface fetchAPIOptions {
  logoutOn401?: boolean;
}

export const fetchAPI = async (
  input: string,
  init?: RequestInit,
  options?: fetchAPIOptions,
) => {
  const apiUrl = `${baseApiUrl('1.0')}${input}`;
  const csrfToken = getCSRFToken();

  const response = await fetch(apiUrl, {
    ...init,
    credentials: 'include',
    headers: {
      ...init?.headers,
      'Content-Type': 'application/json',
      ...(csrfToken && { 'X-CSRFToken': csrfToken }),
    },
  });

  if ((options?.logoutOn401 ?? true) && response.status === 401) {
    logout();
  }

  return response;
};
