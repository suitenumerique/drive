import clsx from "clsx";
import { ReactNode } from "react";
import type { StaticImageData } from "next/image";

import shieldCheck from "@/assets/encryption/shield-check.png";
import shieldX from "@/assets/encryption/shield-x.png";
import documentShieldCheck from "@/assets/encryption/document-shield-check.png";
import documentShieldX from "@/assets/encryption/document-shield-x.png";
import documentEncrypted from "@/assets/encryption/document-encrypted.svg";
import documentEncrypting from "@/assets/encryption/document-encrypting.svg";
import folderDrive from "@/assets/encryption/folder-drive.svg";
import folderInfoShieldCheck from "@/assets/encryption/folder-info-shield-check.svg";

const MODAL_ILLUSTRATIONS = {
  "shield-check": shieldCheck,
  "shield-x": shieldX,
  "document-shield-check": documentShieldCheck,
  "document-shield-x": documentShieldX,
} satisfies Record<string, StaticImageData>;

const STATE_ILLUSTRATIONS = {
  "document-encrypted": documentEncrypted,
  "document-encrypting": documentEncrypting,
} satisfies Record<string, StaticImageData>;

export type ModalIllustration =
  | keyof typeof MODAL_ILLUSTRATIONS
  | "folder-shield";
export type StateIllustration = keyof typeof STATE_ILLUSTRATIONS;

/** A folder with the shield badge of encrypted content. */
const FolderShieldIllustration = () => (
  <div className="drive__encryption-folder-shield" aria-hidden>
    <img
      className="drive__encryption-folder-shield__folder"
      src={folderDrive.src}
      alt=""
    />
    <span className="drive__encryption-folder-shield__badge">
      <img src={folderInfoShieldCheck.src} alt="" />
    </span>
  </div>
);

interface EncryptionModalContentProps {
  illustration?: ModalIllustration;
  title: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
  actions?: ReactNode;
  actionsLayout?: "stack" | "row";
  className?: string;
}

/**
 * The content of an encryption modal: illustration, title, description, body
 * and stacked full-width actions. Rendered inside a Cunningham small modal
 * (widened to 350px by `Encryption.scss`) with the modal's own close control.
 */
export const EncryptionModalContent = ({
  illustration,
  title,
  description,
  children,
  actions,
  actionsLayout = "stack",
  className,
}: EncryptionModalContentProps) => (
  <div className={clsx("drive__encryption-modal", className)}>
    {illustration && (
      <div className="drive__encryption-modal__illustration">
        {illustration === "folder-shield" ? (
          <FolderShieldIllustration />
        ) : (
          <img src={MODAL_ILLUSTRATIONS[illustration].src} alt="" />
        )}
      </div>
    )}
    <div className="drive__encryption-modal__header">
      <h2 className="drive__encryption-modal__title">{title}</h2>
      {description && (
        <p className="drive__encryption-modal__description">{description}</p>
      )}
    </div>
    {children && (
      <div className="drive__encryption-modal__body">{children}</div>
    )}
    {actions && (
      <div
        className={
          actionsLayout === "row"
            ? "drive__encryption-modal__actions drive__encryption-modal__actions--row"
            : "drive__encryption-modal__actions"
        }
      >
        {actions}
      </div>
    )}
  </div>
);

interface EncryptionStateProps {
  illustration?: StateIllustration;
  title: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
  actions?: ReactNode;
}

/**
 * A compact centered state inside the file viewer or a page: illustration,
 * bold title, short description and text-link actions.
 */
export const EncryptionState = ({
  illustration = "document-encrypted",
  title,
  description,
  children,
  actions,
}: EncryptionStateProps) => (
  <div className="drive__encryption-state">
    <div className="drive__encryption-state__content">
      <img
        className="drive__encryption-state__illustration"
        src={STATE_ILLUSTRATIONS[illustration].src}
        alt=""
      />
      <p className="drive__encryption-state__title">{title}</p>
      {description && (
        <p className="drive__encryption-state__description">{description}</p>
      )}
    </div>
    {children}
    {actions && (
      <div className="drive__encryption-state__actions">{actions}</div>
    )}
  </div>
);
