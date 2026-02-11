import { AppError } from "./AppError";

export type UploadFailureKind =
  | "create_failed"
  | "put_failed"
  | "finalize_failed"
  | "timeout";

export type UploadNextAction = "retry" | "reinitiate" | "contact_admin";

export class UploadError extends AppError {
  kind: UploadFailureKind;
  nextAction: UploadNextAction;
  itemId?: string;

  constructor(params: {
    message: string;
    kind: UploadFailureKind;
    nextAction: UploadNextAction;
    itemId?: string;
  }) {
    super(params.message);
    this.kind = params.kind;
    this.nextAction = params.nextAction;
    this.itemId = params.itemId;
  }
}

