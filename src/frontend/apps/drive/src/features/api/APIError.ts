/* eslint-disable @typescript-eslint/no-explicit-any */
import i18n from "@/features/i18n/initI18n";

export class APIError extends Error {
  data?: any;
  code: number;

  constructor(code: number, data?: any) {
    super();
    this.data = data;
    this.code = code;
  }
}

export const errorToString = (error: unknown): string => {
  if (typeof error === "string") {
    return error;
  }
  if (error instanceof APIError) {
    // If there is a data, it means that the error is a JSON object
    if (error.data) {
      return errorToString(error.data);
    }
    // If there is no data, it means that the error is a string, probably a complicated html error.
    return i18n.t("api.error.unexpected");
  }
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === "object" && error !== null) {
    /**
     * This is made to handle full text errors from the API like:
     *
     * "title": [
     *   "The title field is required."
     *  ]
     */
    return Object.entries(error)
      .map(([, value]) => `${errorToString(value)}`)
      .join("\n");
  }
  return i18n.t("api.error.unexpected");
};
