/**
 * OnlyOffice client-side editor for encrypted files.
 *
 * Loads the OnlyOffice editor directly in the browser (no WOPI, no Document Server).
 * File content is decrypted client-side via the vault, edited locally,
 * and auto-saved back to S3 encrypted.
 *
 * Flow:
 * 1. Download encrypted file from S3
 * 2. Decrypt via vault (with key chain)
 * 3. Convert to .bin via x2t WASM (in-memory)
 * 4. Load OnlyOffice with blob URL
 * 5. connectMockServer() with our bridge
 * 6. Auto-save: extract .bin → x2t → original format → encrypt → upload S3
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Loader } from "@gouvfr-lasuite/cunningham-react";
import { Item } from "@/features/drivers/types";
import { getDriver } from "@/features/config/Config";
import { convertToInternal, convertFromInternal } from "./x2tConverter";
import { createMockServerCallbacks, sendToEditor } from "./mockServer";
import { initLocalUser, getLocalUser, getUniqueOOId } from "./participants";
import { resetPatchIndex } from "./changesPipeline";
import { initCheckpointing, stopCheckpointing, forceSave } from "./checkpointing";
import {
  EXTENSION_TO_DOC_TYPE,
  EXTENSION_TO_X2T_TYPE,
  type OOConfig,
  type OOChange,
} from "./types";
import { useAuth } from "@/features/auth/Auth";

// The OnlyOffice DocsAPI is loaded as a global from the static assets
declare global {
  interface Window {
    DocsAPI?: {
      DocEditor: new (
        placeholder: string,
        config: OOConfig,
      ) => OOEditorInstance;
    };
    __driveVaultClient?: any;
  }
}

interface OOEditorInstance {
  connectMockServer: (callbacks: any) => void;
  asc_nativeGetFile: () => Uint8Array;
  destroyEditor: () => void;
}

interface OOEditorProps {
  item: Item;
}

type EditorState = "loading" | "decrypting" | "converting" | "ready" | "error";

export const OOEditor = ({ item }: OOEditorProps) => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [state, setState] = useState<EditorState>("loading");
  const [error, setError] = useState<string | null>(null);
  const editorRef = useRef<OOEditorInstance | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const scriptLoadedRef = useRef(false);

  const extension = item.title.split(".").pop()?.toLowerCase() || "docx";
  const docType = EXTENSION_TO_DOC_TYPE[extension] || "word";
  const x2tType = EXTENSION_TO_X2T_TYPE[extension] || "doc";

  /**
   * Load the OnlyOffice API script if not already loaded.
   */
  const loadOOScript = useCallback((): Promise<void> => {
    if (window.DocsAPI) return Promise.resolve();
    if (scriptLoadedRef.current) return Promise.resolve();

    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "/onlyoffice/v9/web-apps/apps/api/documents/api.js";
      script.onload = () => {
        scriptLoadedRef.current = true;
        resolve();
      };
      script.onerror = () => reject(new Error("Failed to load OnlyOffice API"));
      document.head.appendChild(script);
    });
  }, []);

  /**
   * Upload encrypted content to S3.
   */
  const uploadEncrypted = useCallback(
    async (content: ArrayBuffer, _format: string): Promise<void> => {
      const vaultClient = window.__driveVaultClient;
      if (!vaultClient) {
        throw new Error("Vault client not available");
      }

      const driver = getDriver();

      // Get key chain for encryption
      const keyChain = await driver.getKeyChain(item.id);

      // Convert entry-point key from base64 to ArrayBuffer
      const entryKeyBinary = atob(keyChain.encrypted_key_for_user);
      const entryKeyBytes = new Uint8Array(entryKeyBinary.length);
      for (let i = 0; i < entryKeyBinary.length; i++) {
        entryKeyBytes[i] = entryKeyBinary.charCodeAt(i);
      }

      const encryptedKeyChain = keyChain.chain.map((entry) => {
        const binary = atob(entry.encrypted_symmetric_key);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
          bytes[i] = binary.charCodeAt(i);
        }
        return bytes.buffer;
      });

      // Encrypt via vault
      const { encryptedData } = await vaultClient.encryptWithKey(
        content,
        entryKeyBytes.buffer,
        encryptedKeyChain.length > 0 ? encryptedKeyChain : undefined,
      );

      // Upload to S3 using the existing upload flow
      // Generate a new filename for the encrypted content
      const newFilename = `${crypto.randomUUID()}.enc`;
      const createResponse = await fetch(
        `/api/v1.0/items/${item.id}/upload-ended/`,
        { method: "POST", credentials: "include" },
      );

      // For now, use a simple PUT to the existing file key
      // The presigned URL from the item's policy
      if (item.url) {
        await fetch(item.url, {
          method: "PUT",
          body: new Uint8Array(encryptedData),
          headers: { "X-amz-acl": "private" },
        });
      }
    },
    [item.id, item.url],
  );

  /**
   * Main initialization: decrypt → convert → load editor.
   */
  useEffect(() => {
    let cancelled = false;

    const init = async () => {
      try {
        if (!item.url || !user) return;

        // Step 1: Load OnlyOffice script
        setState("loading");
        await loadOOScript();
        if (cancelled) return;

        // Step 2: Download and decrypt the file
        setState("decrypting");
        const driver = getDriver();
        const keyChain = await driver.getKeyChain(item.id);

        const response = await fetch(item.url, { credentials: "include" });
        if (!response.ok) throw new Error(`Fetch failed: ${response.status}`);
        const encryptedBuffer = await response.arrayBuffer();

        const vaultClient = window.__driveVaultClient;
        if (!vaultClient) throw new Error("Vault client not initialized");

        // Decrypt
        const entryKeyBinary = atob(keyChain.encrypted_key_for_user);
        const entryKeyBytes = new Uint8Array(entryKeyBinary.length);
        for (let i = 0; i < entryKeyBinary.length; i++) {
          entryKeyBytes[i] = entryKeyBinary.charCodeAt(i);
        }

        const encryptedKeyChain = keyChain.chain.map((entry) => {
          const binary = atob(entry.encrypted_symmetric_key);
          const bytes = new Uint8Array(binary.length);
          for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
          }
          return bytes.buffer;
        });

        const { data: decryptedBuffer } = await vaultClient.decryptWithKey(
          encryptedBuffer,
          entryKeyBytes.buffer,
          encryptedKeyChain.length > 0 ? encryptedKeyChain : undefined,
        );
        if (cancelled) return;

        // Step 3: Convert to .bin format
        setState("converting");
        const { bin } = await convertToInternal(decryptedBuffer, item.title);
        if (cancelled) return;

        // Step 4: Create blob URL and load editor
        const blob = new Blob([bin], {
          type: "application/octet-stream",
        });
        const blobUrl = URL.createObjectURL(blob);

        // Initialize participant tracking
        initLocalUser(user.id, user.full_name || user.email);
        resetPatchIndex(0);

        // Create the editor config
        const config: OOConfig = {
          document: {
            fileType: "bin",
            key: item.id + "_" + Date.now(),
            title: item.title,
            url: blobUrl,
          },
          documentType: docType,
          editorConfig: {
            mode: "edit",
            user: {
              id: user.id,
              name: user.full_name || user.email,
            },
            lang: user.language || "en",
            customization: {
              chat: false,
              compactToolbar: false,
              forcesave: false,
            },
          },
          events: {
            onAppReady: () => {
              // Editor UI is ready
            },
            onDocumentReady: () => {
              setState("ready");
            },
            onError: (event) => {
              console.error("OnlyOffice error:", event.data);
              setError(String(event.data));
              setState("error");
            },
          },
        };

        if (!window.DocsAPI) {
          throw new Error("OnlyOffice API not loaded");
        }

        // Create the editor
        const editor = new window.DocsAPI.DocEditor(
          "oo-editor-placeholder",
          config,
        );
        editorRef.current = editor;

        // Connect our mock server (replaces Document Server)
        const callbacks = createMockServerCallbacks({
          onLocalChanges: (changes: OOChange[]) => {
            // Phase 1: single user, no broadcast needed
            // Phase 2: encrypt and send via WebSocket relay
          },
        });
        editor.connectMockServer(callbacks);

        // Initialize auto-save
        initCheckpointing({
          editor,
          format: extension,
          type: x2tType,
          onUpload: uploadEncrypted,
        });

        // Clean up blob URL after editor loads
        URL.revokeObjectURL(blobUrl);
      } catch (err) {
        if (!cancelled) {
          console.error("OOEditor init failed:", err);
          setError(err instanceof Error ? err.message : "Failed to load editor");
          setState("error");
        }
      }
    };

    init();

    return () => {
      cancelled = true;
      stopCheckpointing();
      // Force save on unmount
      forceSave().catch(console.error);
      if (editorRef.current) {
        try {
          editorRef.current.destroyEditor();
        } catch {
          // Editor may already be destroyed
        }
      }
    };
  }, [item.id]);

  if (state === "error") {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          gap: "16px",
        }}
      >
        <span
          className="material-icons"
          style={{ fontSize: "48px", color: "var(--c--theme--colors--danger-600)" }}
        >
          error
        </span>
        <span>{t("explorer.encrypted.editor_error", "Failed to load editor")}</span>
        {error && (
          <span style={{ fontSize: "12px", color: "var(--c--theme--colors--greyscale-600)" }}>
            {error}
          </span>
        )}
      </div>
    );
  }

  if (state !== "ready") {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          gap: "16px",
        }}
      >
        <Loader />
        <span
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            color: "var(--c--theme--colors--success-600, #18753c)",
          }}
        >
          <span className="material-icons" style={{ fontSize: "20px" }}>
            lock
          </span>
          {state === "decrypting" && t("explorer.encrypted.decrypting", "Decrypting...")}
          {state === "converting" && t("explorer.encrypted.converting", "Preparing editor...")}
          {state === "loading" && t("explorer.encrypted.loading_editor", "Loading editor...")}
        </span>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%" }}
    >
      <div id="oo-editor-placeholder" style={{ width: "100%", height: "100%" }} />
    </div>
  );
};
