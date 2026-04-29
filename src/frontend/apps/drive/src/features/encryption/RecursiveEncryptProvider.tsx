/**
 * App-level host for the recursive-encryption modals.
 *
 * Some move flows can't complete in-place because they cross an
 * encryption boundary:
 *   - plaintext → encrypted folder: encrypt the source first
 *   - encrypted → plaintext folder: decrypt the source first
 *
 * The driver throws `MoveRequiresEncryption`; the call site catches it
 * and uses the context exposed here to ask "please {en,de}crypt this
 * item, resolve when done". The matching modal renders, the promise
 * settles when the user closes it.
 *
 * Items are processed sequentially: one modal at a time, others queue.
 */
import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
} from 'react';
import type { ReactNode } from 'react';
import { ModalRecursiveEncrypt } from './ModalRecursiveEncrypt';
import { ModalRecursiveRemoveEncryption } from './ModalRecursiveRemoveEncryption';
import type { Item } from '@/features/drivers/types';

/** Sentinel error so callers can distinguish "user cancelled" from a real failure. */
export class EncryptionRequestCancelled extends Error {
  constructor(public readonly itemId: string) {
    super(`User closed the encryption modal before completion for ${itemId}`);
    this.name = 'EncryptionRequestCancelled';
  }
}

type Mode = 'encrypt' | 'decrypt';

interface PendingRequest {
  mode: Mode;
  item: Item;
  resolve: () => void;
  reject: (e: unknown) => void;
  /** Set to `true` when the modal's recursive job reports success. */
  succeeded: boolean;
  /**
   * When set, the encrypt request is an encrypt-on-move: the modal
   * runs the recursive job in 'encrypt-into-chain' mode, which produces
   * a chain-rooted item and commits move + encryption in a single
   * /move/ call. Caller doesn't need to follow up with a separate
   * `driver.moveItem` — the job handles it.
   */
  intoChainParentId?: string;
}

interface ContextValue {
  /**
   * Open the recursive-encryption modal for `item` and resolve when
   * the encryption completes. Rejects with `EncryptionRequestCancelled`
   * if the user closes the modal before success.
   *
   * Optional `options.intoChainParentId` switches to encrypt-on-move
   * mode: the modal performs both the encryption AND the move into the
   * given parent atomically. The caller must NOT issue a separate
   * `moveItem` afterwards; the resolve already reflects both having
   * happened.
   */
  requestEncryption: (
    item: Item,
    options?: { intoChainParentId?: string },
  ) => Promise<void>;
  /**
   * Open the recursive-decryption modal for `item` and resolve when
   * the decryption completes. Same cancellation contract.
   */
  requestDecryption: (item: Item) => Promise<void>;
}

const RecursiveEncryptContext = createContext<ContextValue>({
  requestEncryption: () =>
    Promise.reject(new Error('No RecursiveEncryptProvider in tree')),
  requestDecryption: () =>
    Promise.reject(new Error('No RecursiveEncryptProvider in tree')),
});

export function RecursiveEncryptProvider({ children }: { children: ReactNode }) {
  // Single in-flight request — sequential UX.
  const [active, setActive] = useState<PendingRequest | null>(null);
  // Pending queue waiting for the active modal to close before being shown.
  const queueRef = useRef<Array<PendingRequest>>([]);
  // Mirror of `active` read at call-time, not at render-time. The modal
  // schedules `setTimeout(onClose, 1200)` from its `onSuccess` callback;
  // that timeout captures the `handleClose` closure that existed when
  // `onSuccess` fired — i.e. the one bound to active.succeeded=false.
  // Reading from this ref instead lets `handleClose` see the up-to-date
  // succeeded flag set by `handleSuccess`, otherwise the modal would
  // always reject with EncryptionRequestCancelled even on a successful
  // run (and the move retry would never fire downstream).
  const activeRef = useRef<PendingRequest | null>(null);

  const startNext = useCallback(() => {
    const next = queueRef.current.shift() ?? null;
    activeRef.current = next;
    setActive(next);
  }, []);

  const enqueue = useCallback(
    (mode: Mode, item: Item, intoChainParentId?: string) => {
      return new Promise<void>((resolve, reject) => {
        const req: PendingRequest = {
          mode,
          item,
          resolve,
          reject,
          succeeded: false,
          intoChainParentId,
        };
        if (activeRef.current === null) {
          activeRef.current = req;
          setActive(req);
        } else {
          queueRef.current.push(req);
        }
      });
    },
    [],
  );

  const requestEncryption = useCallback(
    (item: Item, options?: { intoChainParentId?: string }) =>
      enqueue('encrypt', item, options?.intoChainParentId),
    [enqueue],
  );
  const requestDecryption = useCallback(
    (item: Item) => enqueue('decrypt', item),
    [enqueue],
  );

  const handleClose = useCallback(() => {
    const current = activeRef.current;
    if (!current) return;
    if (current.succeeded) {
      current.resolve();
    } else {
      current.reject(new EncryptionRequestCancelled(current.item.id));
    }
    startNext();
  }, [startNext]);

  const handleSuccess = useCallback(() => {
    if (activeRef.current) {
      activeRef.current.succeeded = true;
    }
  }, []);

  return (
    <RecursiveEncryptContext.Provider
      value={{ requestEncryption, requestDecryption }}
    >
      {children}
      {active?.mode === 'encrypt' && (
        <ModalRecursiveEncrypt
          isOpen
          item={active.item}
          intoChainParentId={active.intoChainParentId}
          onSuccess={handleSuccess}
          onClose={handleClose}
        />
      )}
      {active?.mode === 'decrypt' && (
        <ModalRecursiveRemoveEncryption
          isOpen
          item={active.item}
          onSuccess={handleSuccess}
          onClose={handleClose}
        />
      )}
    </RecursiveEncryptContext.Provider>
  );
}

export const useRecursiveEncrypt = () => useContext(RecursiveEncryptContext);
