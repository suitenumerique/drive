import { useCallback, useEffect, useReducer, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useQueryClient } from '@tanstack/react-query';
import { Item, ItemType, LinkReach } from '@/features/drivers/types';
import { getDriver } from '@/features/config/Config';
import { APIError } from '@/features/api/APIError';
import { useAuth } from '@/features/auth/Auth';
import { useVaultClient } from '../VaultClientProvider';
import { fetchSubtree, filesOnly } from './flattenSubtree';
import { fromBase64, stagedFilename, toBase64 } from './binary';
import { getEncryptionUploadUrl, putToS3 } from './presignedUpload';
import {
  FileJobRow,
  FileJobState,
  FlatNode,
  JobPhase,
  SkipReason,
  StagedEncryptFile,
} from './types';

type Mode = 'encrypt' | 'decrypt';

type State = {
  phase: JobPhase;
  rows: FileJobRow[];
  rowIndexById: Record<string, number>;
  topError: string | null;
  validationErrors: string[];
  totalProcessable: number;
};

type Action =
  | { type: 'SET_PHASE'; phase: JobPhase }
  | { type: 'SET_ROWS'; rows: FileJobRow[] }
  | {
      type: 'UPDATE_ROW';
      id: string;
      state: FileJobState;
      error?: string;
      skipReason?: SkipReason;
    }
  | { type: 'SET_TOP_ERROR'; error: string | null }
  | { type: 'SET_VALIDATION'; errors: string[] }
  | { type: 'PROMOTE_STAGED_TO_DONE' }
  | { type: 'RESET_FAILED_TO_PENDING' }
  | { type: 'RESET' };

const CONCURRENCY = 3;

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'SET_PHASE':
      return { ...state, phase: action.phase };
    case 'SET_ROWS': {
      const rowIndexById: Record<string, number> = {};
      action.rows.forEach((r, i) => {
        rowIndexById[r.id] = i;
      });
      const totalProcessable = action.rows.filter(
        (r) => r.state !== 'skipped',
      ).length;
      return { ...state, rows: action.rows, rowIndexById, totalProcessable };
    }
    case 'UPDATE_ROW': {
      const idx = state.rowIndexById[action.id];
      if (idx === undefined) return state;
      const next = state.rows.slice();
      next[idx] = {
        ...next[idx],
        state: action.state,
        error: action.error,
        skipReason: action.skipReason ?? next[idx].skipReason,
      };
      return { ...state, rows: next };
    }
    case 'SET_TOP_ERROR':
      return { ...state, topError: action.error };
    case 'SET_VALIDATION':
      return { ...state, validationErrors: action.errors };
    case 'PROMOTE_STAGED_TO_DONE': {
      const next = state.rows.map((r) =>
        r.state === 'staged' ? { ...r, state: 'done' as FileJobState } : r,
      );
      return { ...state, rows: next };
    }
    case 'RESET_FAILED_TO_PENDING': {
      const next = state.rows.map((r) =>
        r.state === 'failed'
          ? { ...r, state: 'pending' as FileJobState, error: undefined }
          : r,
      );
      return { ...state, rows: next };
    }
    case 'RESET':
      return INITIAL;
    default:
      return state;
  }
}

const INITIAL: State = {
  phase: 'discovering',
  rows: [],
  rowIndexById: {},
  topError: null,
  validationErrors: [],
  totalProcessable: 0,
};

export type UseRecursiveEncryptionJobArgs = {
  mode: Mode;
  item: Item;
  isOpen: boolean;
  onSuccess?: () => void;
};

export type UseRecursiveEncryptionJob = {
  phase: JobPhase;
  rows: FileJobRow[];
  totalProcessable: number;
  doneCount: number;
  skippedCount: number;
  failedCount: number;
  validationErrors: string[];
  topError: string | null;
  canConfirm: boolean;
  confirm: () => void;
  retry: () => void;
  cancel: () => void;
};

/**
 * Discover → validate → stage (worker pool) → single-shot commit.
 *
 * Atomicity: staging uploads N blobs to S3 under fresh keys, then ONE backend
 * PATCH commits the whole fileKeyMapping + encryptedKeysForDescendants in a
 * DB transaction. Failure pre-commit ⇒ DB untouched; rollback is `return;`.
 */
export function useRecursiveEncryptionJob({
  mode,
  item,
  isOpen,
  onSuccess,
}: UseRecursiveEncryptionJobArgs): UseRecursiveEncryptionJob {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { client: vaultClient } = useVaultClient();
  const { user } = useAuth();

  const [state, dispatch] = useReducer(reducer, INITIAL);

  const abortRef = useRef<AbortController | null>(null);
  const flatRef = useRef<FlatNode[]>([]);
  const processableIdsRef = useRef<string[]>([]);
  const publicKeysRef = useRef<Record<string, ArrayBuffer>>({});
  // For encrypt mode, the root's per-user wrapped key map (committed).
  const rootEncryptedKeysRef = useRef<Record<string, ArrayBuffer>>({});
  // Current user's wrapped copy of the root key — entry key for
  // encryptWithKey on descendants.
  const currentUserRootWrappedRef = useRef<ArrayBuffer | null>(null);

  useEffect(() => {
    if (!isOpen) {
      abortRef.current?.abort();
      abortRef.current = null;
      flatRef.current = [];
      processableIdsRef.current = [];
      publicKeysRef.current = {};
      rootEncryptedKeysRef.current = {};
      currentUserRootWrappedRef.current = null;
      dispatch({ type: 'RESET' });
    }
  }, [isOpen]);

  // Discovery + validation when the modal opens.
  useEffect(() => {
    if (!isOpen || !vaultClient || !user?.sub) return;

    let cancelled = false;
    const run = async () => {
      try {
        dispatch({ type: 'SET_PHASE', phase: 'discovering' });

        const driver = getDriver();
        const flat =
          item.type === ItemType.FOLDER
            ? await fetchSubtree(driver, item)
            : [{ item, parentId: null, depth: 0, pathCrumb: '' }];
        if (cancelled) return;
        flatRef.current = flat;

        const sourceNodes =
          item.type === ItemType.FILE ? flat : filesOnly(flat);

        const rows: FileJobRow[] = sourceNodes.map((n) => {
          const shouldSkip =
            mode === 'encrypt' ? !!n.item.is_encrypted : !n.item.is_encrypted;
          return {
            id: n.item.id,
            title: n.item.title,
            path: n.pathCrumb,
            state: shouldSkip ? 'skipped' : 'pending',
            skipReason: shouldSkip
              ? mode === 'encrypt'
                ? 'already_encrypted'
                : 'not_encrypted'
              : undefined,
          };
        });

        dispatch({ type: 'SET_ROWS', rows });
        processableIdsRef.current = rows
          .filter((r) => r.state === 'pending')
          .map((r) => r.id);

        dispatch({ type: 'SET_PHASE', phase: 'validating' });

        const errors: string[] = [];

        if (mode === 'encrypt') {
          const effectiveReach =
            item.computed_link_reach ?? item.link_reach ?? null;
          if (effectiveReach && effectiveReach !== LinkReach.RESTRICTED) {
            errors.push(
              t(
                'encryption.errors.not_restricted',
                'The item must have restricted access (no public or authenticated link).',
              ),
            );
          }

          const userIds = item.accesses_user_ids ?? [];
          if (userIds.length === 0) {
            errors.push(
              t(
                'encryption.errors.no_accesses',
                'No users with access found on the root item.',
              ),
            );
          }

          if (processableIdsRef.current.length === 0) {
            errors.push(
              t(
                'encryption.errors.nothing_to_encrypt',
                'Nothing to encrypt — every file in the selection is already encrypted.',
              ),
            );
          }

          if (errors.length === 0 && userIds.length > 0) {
            const { publicKeys } = await vaultClient.fetchPublicKeys(userIds);
            if (cancelled) return;

            const missing = userIds.filter((uid) => !publicKeys[uid]);
            if (missing.length > 0) {
              errors.push(
                t(
                  'encryption.errors.missing_keys',
                  "{{count}} user(s) don't have encryption enabled yet.",
                  { count: missing.length },
                ),
              );
            } else {
              publicKeysRef.current = publicKeys;
            }
          }
        } else {
          if (processableIdsRef.current.length === 0) {
            errors.push(
              t(
                'encryption.errors.nothing_to_decrypt',
                'Nothing to decrypt — every file in the selection is already plaintext.',
              ),
            );
          }
        }

        dispatch({ type: 'SET_VALIDATION', errors });

        if (errors.length > 0) {
          dispatch({ type: 'SET_PHASE', phase: 'failed' });
          return;
        }

        dispatch({ type: 'SET_PHASE', phase: 'ready' });
      } catch (err) {
        if (cancelled) return;
        dispatch({ type: 'SET_TOP_ERROR', error: (err as Error).message });
        dispatch({ type: 'SET_PHASE', phase: 'failed' });
      }
    };

    void run();

    return () => {
      cancelled = true;
    };
  }, [isOpen, vaultClient, user?.sub, item, mode, t]);

  const confirm = useCallback(async () => {
    if (!vaultClient || !user?.sub) return;

    const controller = new AbortController();
    abortRef.current = controller;
    dispatch({ type: 'SET_PHASE', phase: 'staging' });

    const stagedResults = new Map<
      string,
      StagedEncryptFile | { newFilename: string }
    >();

    try {
      if (mode === 'encrypt') {
        await encryptPipeline({
          vaultClient,
          currentUserId: user.sub!,
          rootItem: item,
          flat: flatRef.current,
          processableIds: processableIdsRef.current,
          publicKeys: publicKeysRef.current,
          rootEncryptedKeysRef,
          currentUserRootWrappedRef,
          signal: controller.signal,
          dispatch,
          onFileStaged: (id, staged) => stagedResults.set(id, staged),
        });
      } else {
        await decryptPipeline({
          vaultClient,
          flat: flatRef.current,
          processableIds: processableIdsRef.current,
          signal: controller.signal,
          dispatch,
          onFileStaged: (id, staged) => stagedResults.set(id, staged),
        });
      }

      dispatch({ type: 'SET_PHASE', phase: 'committing' });

      const driver = getDriver();
      if (mode === 'encrypt') {
        const fileKeyMapping: Record<string, string> = {};
        const encryptedKeysForDescendants: Record<string, string> = {};
        stagedResults.forEach((v, id) => {
          fileKeyMapping[id] = v.newFilename;
          if ('wrappedKey' in v && v.wrappedKey && v.wrappedKey.byteLength > 0) {
            encryptedKeysForDescendants[id] = toBase64(v.wrappedKey);
          }
        });

        const encryptedSymmetricKeyPerUser: Record<string, string> = {};
        for (const [uid, buf] of Object.entries(rootEncryptedKeysRef.current)) {
          encryptedSymmetricKeyPerUser[uid] = toBase64(buf);
        }

        await driver.encryptItem(item.id, {
          encryptedSymmetricKeyPerUser,
          encryptedKeysForDescendants,
          fileKeyMapping,
        });
      } else {
        const fileKeyMapping: Record<string, string> = {};
        stagedResults.forEach((v, id) => {
          fileKeyMapping[id] = v.newFilename;
        });
        await driver.removeEncryption(item.id, { fileKeyMapping });
      }

      dispatch({ type: 'PROMOTE_STAGED_TO_DONE' });
      await queryClient.invalidateQueries({ queryKey: ['items'] });

      dispatch({ type: 'SET_PHASE', phase: 'success' });
      onSuccess?.();
    } catch (err) {
      if (
        controller.signal.aborted &&
        (err as Error).name === 'AbortError'
      ) {
        return;
      }
      let message = (err as Error).message;
      if (err instanceof APIError && err.data?.code === 'subtree_mutated') {
        const missing = (err.data.missing as string[] | undefined) ?? [];
        const extra = (err.data.extra as string[] | undefined) ?? [];
        message = t(
          'encryption.errors.subtree_mutated',
          'The folder contents changed during the operation ({{added}} added, {{removed}} removed). Close this dialog and try again.',
          { added: missing.length, removed: extra.length },
        );
      }
      dispatch({ type: 'SET_TOP_ERROR', error: message });
      dispatch({ type: 'SET_PHASE', phase: 'failed' });
    }
  }, [mode, vaultClient, user?.sub, item, queryClient, onSuccess, t]);

  const retry = useCallback(() => {
    dispatch({ type: 'RESET_FAILED_TO_PENDING' });
    dispatch({ type: 'SET_TOP_ERROR', error: null });
    void confirm();
  }, [confirm]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const doneCount = state.rows.filter(
    (r) => r.state === 'done' || r.state === 'staged',
  ).length;
  const skippedCount = state.rows.filter((r) => r.state === 'skipped').length;
  const failedCount = state.rows.filter((r) => r.state === 'failed').length;

  const canConfirm =
    state.phase === 'ready' &&
    state.validationErrors.length === 0 &&
    processableIdsRef.current.length > 0;

  return {
    phase: state.phase,
    rows: state.rows,
    totalProcessable: state.totalProcessable,
    doneCount,
    skippedCount,
    failedCount,
    validationErrors: state.validationErrors,
    topError: state.topError,
    canConfirm,
    confirm,
    retry,
    cancel,
  };
}

// ---------- Pipelines ----------

type DispatchFn = (action: Action) => void;

type EncryptPipelineArgs = {
  vaultClient: VaultClient;
  currentUserId: string;
  rootItem: Item;
  flat: FlatNode[];
  processableIds: string[];
  publicKeys: Record<string, ArrayBuffer>;
  rootEncryptedKeysRef: React.MutableRefObject<Record<string, ArrayBuffer>>;
  currentUserRootWrappedRef: React.MutableRefObject<ArrayBuffer | null>;
  signal: AbortSignal;
  dispatch: DispatchFn;
  onFileStaged: (id: string, staged: StagedEncryptFile) => void;
};

async function encryptPipeline({
  vaultClient,
  currentUserId,
  rootItem,
  flat,
  processableIds,
  publicKeys,
  rootEncryptedKeysRef,
  currentUserRootWrappedRef,
  signal,
  dispatch,
  onFileStaged,
}: EncryptPipelineArgs): Promise<void> {
  // Root-key minting happens before per-file staging only when the root
  // is a FOLDER. When the root is a FILE, the root IS the per-file case
  // and encryptWithoutKey is called with the actual file content below.
  if (rootItem.type === ItemType.FOLDER) {
    const { encryptedKeys } = await vaultClient.encryptWithoutKey(
      new ArrayBuffer(0),
      publicKeys,
    );
    if (signal.aborted) throw abortError();
    rootEncryptedKeysRef.current = encryptedKeys;
    const currentUserWrapped = encryptedKeys[currentUserId];
    if (!currentUserWrapped) {
      throw new Error(
        'Current user has no wrapped root key — encryption keys not set up.',
      );
    }
    currentUserRootWrappedRef.current = currentUserWrapped;
  }

  const queue = [...processableIds];
  const worker = async (): Promise<void> => {
    while (queue.length > 0) {
      if (signal.aborted) throw abortError();
      const id = queue.shift();
      if (!id) return;
      await stageOneEncryption({
        vaultClient,
        rootItem,
        flat,
        targetId: id,
        publicKeys,
        rootEncryptedKeysRef,
        currentUserRootWrappedRef,
        signal,
        dispatch,
        onFileStaged,
      });
    }
  };
  await Promise.all(Array.from({ length: CONCURRENCY }, () => worker()));
  void currentUserId;
}

type StageOneEncryptArgs = {
  vaultClient: VaultClient;
  rootItem: Item;
  flat: FlatNode[];
  targetId: string;
  publicKeys: Record<string, ArrayBuffer>;
  rootEncryptedKeysRef: React.MutableRefObject<Record<string, ArrayBuffer>>;
  currentUserRootWrappedRef: React.MutableRefObject<ArrayBuffer | null>;
  signal: AbortSignal;
  dispatch: DispatchFn;
  onFileStaged: (id: string, staged: StagedEncryptFile) => void;
};

async function stageOneEncryption({
  vaultClient,
  rootItem,
  flat,
  targetId,
  publicKeys,
  rootEncryptedKeysRef,
  currentUserRootWrappedRef,
  signal,
  dispatch,
  onFileStaged,
}: StageOneEncryptArgs): Promise<void> {
  const node = flat.find((n) => n.item.id === targetId);
  if (!node) throw new Error(`Row ${targetId} not found in tree`);

  dispatch({ type: 'UPDATE_ROW', id: targetId, state: 'running' });

  try {
    if (signal.aborted) throw abortError();

    const resp = await fetch(node.item.url!, {
      credentials: 'include',
      signal,
    });
    if (!resp.ok) {
      throw new Error(`Download failed: ${resp.status}`);
    }
    const plaintext = await resp.arrayBuffer();

    let encryptedContent: ArrayBuffer;
    let wrappedKey: ArrayBuffer;

    if (rootItem.type === ItemType.FILE && targetId === rootItem.id) {
      const { encryptedContent: ct, encryptedKeys } =
        await vaultClient.encryptWithoutKey(plaintext, publicKeys);
      encryptedContent = ct;
      rootEncryptedKeysRef.current = encryptedKeys;
      wrappedKey = new ArrayBuffer(0);
    } else {
      const entryKey = currentUserRootWrappedRef.current;
      if (!entryKey) throw new Error('Missing root entry key');
      const { encryptedData, wrappedKey: wk } =
        await vaultClient.encryptWithKey(plaintext, entryKey);
      encryptedContent = encryptedData;
      wrappedKey = wk;
    }

    const newFilename = stagedFilename(node.item.title);
    const uploadUrl = await getEncryptionUploadUrl(
      targetId,
      newFilename,
      signal,
    );
    await putToS3(uploadUrl, encryptedContent, signal);

    onFileStaged(targetId, { itemId: targetId, newFilename, wrappedKey });
    dispatch({ type: 'UPDATE_ROW', id: targetId, state: 'staged' });
  } catch (err) {
    if ((err as Error).name === 'AbortError') throw err;
    dispatch({
      type: 'UPDATE_ROW',
      id: targetId,
      state: 'failed',
      error: (err as Error).message,
    });
    throw err;
  }
}

type DecryptPipelineArgs = {
  vaultClient: VaultClient;
  flat: FlatNode[];
  processableIds: string[];
  signal: AbortSignal;
  dispatch: DispatchFn;
  onFileStaged: (id: string, staged: { newFilename: string }) => void;
};

async function decryptPipeline({
  vaultClient,
  flat,
  processableIds,
  signal,
  dispatch,
  onFileStaged,
}: DecryptPipelineArgs): Promise<void> {
  const queue = [...processableIds];
  const worker = async (): Promise<void> => {
    while (queue.length > 0) {
      if (signal.aborted) throw abortError();
      const id = queue.shift();
      if (!id) return;

      const node = flat.find((n) => n.item.id === id);
      if (!node) continue;

      dispatch({ type: 'UPDATE_ROW', id, state: 'running' });

      try {
        const driver = getDriver();
        const keyChain = await driver.getKeyChain(id);
        const entryKey = fromBase64(keyChain.encrypted_key_for_user);
        const chain = keyChain.chain.map((e) =>
          fromBase64(e.encrypted_symmetric_key),
        );

        const resp = await fetch(node.item.url!, {
          credentials: 'include',
          signal,
        });
        if (!resp.ok) {
          throw new Error(`Download failed: ${resp.status}`);
        }
        const ciphertext = await resp.arrayBuffer();

        const { data: plaintext } = await vaultClient.decryptWithKey(
          ciphertext,
          entryKey,
          chain.length > 0 ? chain : undefined,
        );

        const newFilename = stagedFilename(node.item.title);
        const uploadUrl = await getEncryptionUploadUrl(id, newFilename, signal);
        await putToS3(uploadUrl, plaintext, signal);

        onFileStaged(id, { newFilename });
        dispatch({ type: 'UPDATE_ROW', id, state: 'staged' });
      } catch (err) {
        if ((err as Error).name === 'AbortError') throw err;
        dispatch({
          type: 'UPDATE_ROW',
          id,
          state: 'failed',
          error: (err as Error).message,
        });
        throw err;
      }
    }
  };
  await Promise.all(Array.from({ length: CONCURRENCY }, () => worker()));
}

function abortError(): Error {
  const e = new Error('Aborted');
  e.name = 'AbortError';
  return e;
}
