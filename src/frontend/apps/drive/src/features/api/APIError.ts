/* eslint-disable @typescript-eslint/no-explicit-any */
import i18n from "@/features/i18n/initI18n";
import { AppError } from "../errors/AppError";

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
      /**
       * This is made to handle full text errors from the API like:
       *
       * "title": [
       *   "The title field is required."
       *  ]
       */
      return Object.entries(error.data)
        .map(([, value]) => `${value}`)
        .join("\n");
    }
    // If there is no data, it means that the error is a string, probably a complicated html error.
    return i18n.t("api.error.unexpected");
  }
  // We want to show the error message from the AppError only. Not message from the Error class as they
  // can be really technical and not helpful for the user. For those we show the generic error message.
  if (error instanceof AppError) {
    return error.message;
  }
  return i18n.t("api.error.unexpected");
};
