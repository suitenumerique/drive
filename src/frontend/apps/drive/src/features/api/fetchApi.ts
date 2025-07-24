import { baseApiUrl, isJson } from "./utils";
import { APIError } from "./APIError";

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

export const SESSION_STORAGE_REDIRECT_AFTER_LOGIN_URL =
  "redirect_after_login_url";

const redirect = (url: string, saveRedirectAfterLoginUrl = true) => {
  if (saveRedirectAfterLoginUrl) {
    sessionStorage.setItem(
      SESSION_STORAGE_REDIRECT_AFTER_LOGIN_URL,
      window.location.href
    );
  }
  window.location.href = url;
};

export interface fetchAPIOptions {
  redirectOn40x?: boolean;
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

  const redirectOn40x = options?.redirectOn40x ?? true;
  if (response.status === 401 && redirectOn40x) {
    redirect("/401");
    // So that the app can handle the error and not show a toast by verifying the error code.
    throw new APIError(response.status);
  }

  if (response.status === 403 && redirectOn40x) {
    // We don't want to save the attempted url when having a 403 error because
    // it would be a redirect loop and it means we know that the user is not
    // allowed to access the page.
    redirect("/403", false);
    // So that the app can handle the error and not show a toast by verifying the error code.
    throw new APIError(response.status);
  }

  if (response.ok) {
    return response;
  }

  const data = await response.text();
  if (isJson(data)) {
    throw new APIError(response.status, JSON.parse(data));
  }
  throw new APIError(response.status);
};
