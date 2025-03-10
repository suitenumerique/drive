import { logout } from "@/features/auth/Auth";
import { baseApiUrl } from "./utils";

/**
 * Retrieves the CSRF token from the document's cookies.
 *
 * @returns {string|null} The CSRF token if found in the cookies, or null if not present.
 */
function getCSRFToken() {
  return document.cookie
    .split(";")
    .filter((cookie) => cookie.trim().startsWith("csrftoken="))
    .map((cookie) => cookie.split("=")[1])
    .pop();
}

export interface fetchAPIOptions {
  logoutOn401?: boolean;
}

export const fetchAPI = async (
  input: string,
  init?: RequestInit & { params?: Record<string, string> },
  options?: fetchAPIOptions
) => {
  const apiUrl = new URL(`${baseApiUrl("1.0")}${input}`);
  if (init?.params) {
    Object.entries(init.params).forEach(([key, value]) => {
      apiUrl.searchParams.set(key, value);
    });
  }
  const csrfToken = getCSRFToken();

  const response = await fetch(apiUrl, {
    ...init,
    credentials: "include",
    headers: {
      ...init?.headers,
      "Content-Type": "application/json",
      ...(csrfToken && { "X-CSRFToken": csrfToken }),
    },
  });

  if ((options?.logoutOn401 ?? true) && response.status === 401) {
    logout();
  }

  return response;
};
