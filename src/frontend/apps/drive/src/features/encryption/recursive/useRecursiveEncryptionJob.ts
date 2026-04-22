import { useCallback, useEffect, useReducer, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useQueryClient } from '@tanstack/react-query';
import { Item, ItemType, LinkReach } from '@/features/drivers/types';
import { getDriver } from '@/features/config/Config';
import { APIError, errorToString } from '@/features/api/APIError';
import { useAuth } from '@/features/auth/Auth';
import { useVaultClient } from '../VaultClientProvider';
import {
  chainForNode,
  fetchSubtree,
  filesOnly,
  foldersOnly,
  innerEncryptionRoots,
  isInsideInnerRoot,
} from './flattenSubtree';
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
  pendingUserCount: number;
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
  | { type: 'SET_PENDING_USER_COUNT'; count: number }
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
        r => r.state !== 'skipped'
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
    case 'SET_PENDING_USER_COUNT':
      return { ...state, pendingUserCount: action.count };
    case 'PROMOTE_STAGED_TO_DONE': {
      const next = state.rows.map(r =>
        r.state === 'staged' ? { ...r, state: 'done' as FileJobState } : r
      );
      return { ...state, rows: next };
    }
    case 'RESET_FAILED_TO_PENDING': {
      const next = state.rows.map(r =>
        r.state === 'failed'
          ? { ...r, state: 'pending' as FileJobState, error: undefined }
          : r
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
  pendingUserCount: 0,
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
  pendingUserCount: number;
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
  const pendingUserIdsRef = useRef<string[]>([]);
  // For encrypt mode, the root's per-user wrapped key map (committed).
  const rootEncryptedKeysRef = useRef<Record<string, ArrayBuffer>>({});
  // Current user's wrapped copy of the root key — entry key for
  // encryptWithKey on descendants.
  const currentUserRootWrappedRef = useRef<ArrayBuffer | null>(null);
  // Wrapped keys of non-root folders in the subtree, keyed by folder id.
  // Populated during the encrypt folder phase; consumed when building each
  // file's chain and merged into encryptedKeysForDescendants at commit.
  const folderWrappedKeysRef = useRef<Map<string, ArrayBuffer>>(new Map());

  useEffect(() => {
    if (!isOpen) {
      abortRef.current?.abort();
      abortRef.current = null;
      flatRef.current = [];
      processableIdsRef.current = [];
      publicKeysRef.current = {};
      pendingUserIdsRef.current = [];
      rootEncryptedKeysRef.current = {};
      currentUserRootWrappedRef.current = null;
      folderWrappedKeysRef.current = new Map();
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

        // For a folder root, show every item in the subtree (the root
        // itself + every descendant folder and file) so the user sees
        // the full scope — including folders, which are also operated
        // on in both modes (key-minted on encrypt, state-cleared on
        // decrypt). For a file root, we only have one node anyway.
        const sourceNodes = flat;

        // For stacked encryption: items inside an inner encryption root
        // stay untouched whether we're encrypting or decrypting the outer
        // root. Skip them in the row list.
        const innerRoots = innerEncryptionRoots(flat, item.id);

        const rows: FileJobRow[] = sourceNodes.map(n => {
          const insideInner = isInsideInnerRoot(n, innerRoots);
          // Uniform: skip if this is_encrypted-state already matches the
          // target state (can't encrypt what's already encrypted, can't
          // decrypt what's already plaintext). Applies to both files and
          // folders — a plaintext folder has nothing to clear on decrypt,
          // an already-encrypted folder has nothing to mint on encrypt.
          const alreadyInTargetState =
            mode === 'encrypt' ? !!n.item.is_encrypted : !n.item.is_encrypted;
          const shouldSkip = insideInner || alreadyInTargetState;
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
        // processableIds feeds the file worker pool, which fetches &
        // uploads content per id. Folders don't have content — their
        // key-minting runs in a separate sequential loop in
        // encryptPipeline — so filter them out here.
        const flatById = new Map(flat.map(n => [n.item.id, n]));
        processableIdsRef.current = rows
          .filter(
            r =>
              r.state === 'pending' &&
              flatById.get(r.id)?.item.type === ItemType.FILE
          )
          .map(r => r.id);

        dispatch({ type: 'SET_PHASE', phase: 'validating' });

        const errors: string[] = [];

        if (mode === 'encrypt') {
          const effectiveReach =
            item.computed_link_reach ?? item.link_reach ?? null;
          if (effectiveReach && effectiveReach !== LinkReach.RESTRICTED) {
            errors.push(
              t(
                'encryption.errors.not_restricted',
                'The item must have restricted access (no public or authenticated link).'
              )
            );
          }

          const userIds = item.accesses_user_ids ?? [];
          if (userIds.length === 0) {
            errors.push(
              t(
                'encryption.errors.no_accesses',
                'No users with access found on the root item.'
              )
            );
          }

          // Only error out when the whole operation is a no-op. For a
          // folder root, encrypting it produces K_root + ItemAccess keys
          // even with no processable descendants (e.g. every descendant
          // file is already inside a stacked inner encryption root, which
          // we leave untouched). For a file root, no processable ids means
          // the file itself is already encrypted — genuine no-op.
          if (
            item.type === ItemType.FILE &&
            processableIdsRef.current.length === 0
          ) {
            errors.push(
              t(
                'encryption.errors.nothing_to_encrypt_file',
                'This file is already encrypted.'
              )
            );
          }

          if (errors.length === 0 && userIds.length > 0) {
            const { publicKeys } = await vaultClient.fetchPublicKeys(userIds);
            if (cancelled) return;

            const missing = userIds.filter(uid => !publicKeys[uid]);
            const callerMissing = user?.sub && missing.includes(user.sub);

            // The caller must have their own key — they're the one about
            // to encrypt, they need to be able to decrypt afterwards.
            if (callerMissing) {
              errors.push(
                t(
                  'encryption.errors.self_missing_key',
                  'You need to complete your encryption onboarding before encrypting this item.'
                )
              );
            } else if (missing.length === userIds.length) {
              // No one on the access list has a key — nobody could
              // decrypt the result. Genuine blocker.
              errors.push(
                t(
                  'encryption.errors.no_keys_at_all',
                  'Nobody with access to this item has completed encryption onboarding.'
                )
              );
            } else {
              // Partial: some users are pending. They'll be written as
              // pending on the backend and accepted later from the share
              // dialog. Informational, not blocking.
              publicKeysRef.current = publicKeys;
              pendingUserIdsRef.current = missing;
              dispatch({
                type: 'SET_PENDING_USER_COUNT',
                count: missing.length,
              });
            }
          }
        } else {
          // For a folder root, decrypting is meaningful even with zero
          // processable files — the root itself needs its ItemAccess
          // keys cleared and its `is_encrypted` flag reset (e.g. when a
          // nested inner root was previously decrypted so there are no
          // encrypted descendants left under this root). For a file
          // root, zero processable means the single file is already
          // plaintext, which is a genuine no-op.
          if (
            item.type === ItemType.FILE &&
            processableIdsRef.current.length === 0
          ) {
            errors.push(
              t(
                'encryption.errors.nothing_to_decrypt_file',
                'This file is already plaintext.'
              )
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
        // Reset folder key map on each attempt (retry recomputes them).
        folderWrappedKeysRef.current = new Map();
        await encryptPipeline({
          vaultClient,
          currentUserId: user.sub!,
          rootItem: item,
          flat: flatRef.current,
          processableIds: processableIdsRef.current,
          publicKeys: publicKeysRef.current,
          rootEncryptedKeysRef,
          currentUserRootWrappedRef,
          folderWrappedKeysRef,
          signal: controller.signal,
          dispatch,
          onFileStaged: (id, staged) => stagedResults.set(id, staged),
        });
      } else {
        await decryptPipeline({
          vaultClient,
          rootItem: item,
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
        // Folder wrappedKeys first (minted top-down in the pipeline),
        // then file wrappedKeys. Backend stores both on Item.encrypted_symmetric_key
        // so /key-chain/ can return the full chain at decrypt time.
        folderWrappedKeysRef.current.forEach((wk, id) => {
          encryptedKeysForDescendants[id] = toBase64(wk);
        });
        stagedResults.forEach((v, id) => {
          fileKeyMapping[id] = v.newFilename;
          if (
            'wrappedKey' in v &&
            v.wrappedKey &&
            v.wrappedKey.byteLength > 0
          ) {
            encryptedKeysForDescendants[id] = toBase64(v.wrappedKey);
          }
        });

        // Contract with /encrypt/: every user on the access list must
        // appear in the payload exactly once. Validated users get their
        // base64 wrapped key; pending users get explicit null.
        const encryptedSymmetricKeyPerUser: Record<string, string | null> = {};
        for (const [uid, buf] of Object.entries(rootEncryptedKeysRef.current)) {
          encryptedSymmetricKeyPerUser[uid] = toBase64(buf);
        }
        for (const uid of pendingUserIdsRef.current) {
          encryptedSymmetricKeyPerUser[uid] = null;
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
      if (controller.signal.aborted && (err as Error).name === 'AbortError') {
        return;
      }
      let message: string;
      if (err instanceof APIError && err.data?.code === 'subtree_mutated') {
        const missing = (err.data.missing as string[] | undefined) ?? [];
        const extra = (err.data.extra as string[] | undefined) ?? [];
        message = t(
          'encryption.errors.subtree_mutated',
          'The folder contents changed during the operation ({{added}} added, {{removed}} removed).',
          { added: missing.length, removed: extra.length }
        );
      } else {
        // APIError has no `.message` (it passes nothing to super), so
        // reading err.message would yield an empty string and the banner
        // would stay blank. errorToString extracts a readable detail from
        // the response body or falls back to the i18n generic string.
        message = errorToString(err);
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
    r => r.state === 'done' || r.state === 'staged'
  ).length;
  const skippedCount = state.rows.filter(r => r.state === 'skipped').length;
  const failedCount = state.rows.filter(r => r.state === 'failed').length;

  // For both folder encrypt and folder decrypt, the operation is
  // meaningful even with zero processable descendants:
  // - encrypt: establish the folder as a new encryption root (stacking
  //   over inner sub-roots that keep their own keys).
  // - decrypt: clear the root's ItemAccess keys and its is_encrypted
  //   flag even when every descendant is already plaintext (e.g. after
  //   an inner root was previously decrypted).
  // Only a file root strictly needs processable content.
  const needsProcessableDescendants = item.type === ItemType.FILE;
  const canConfirm =
    state.phase === 'ready' &&
    state.validationErrors.length === 0 &&
    (!needsProcessableDescendants || processableIdsRef.current.length > 0);

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
    pendingUserCount: state.pendingUserCount,
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
  folderWrappedKeysRef: React.MutableRefObject<Map<string, ArrayBuffer>>;
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
  folderWrappedKeysRef,
  signal,
  dispatch,
  onFileStaged,
}: EncryptPipelineArgs): Promise<void> {
  // Root-key minting happens before per-file staging only when the root
  // is a FOLDER. When the root is a FILE, the root IS the per-file case
  // and encryptWithoutKey is called with the actual file content below.
  if (rootItem.type === ItemType.FOLDER) {
    dispatch({ type: 'UPDATE_ROW', id: rootItem.id, state: 'running' });
    const { encryptedKeys } = await vaultClient.encryptWithoutKey(
      new ArrayBuffer(0),
      publicKeys
    );
    if (signal.aborted) throw abortError();
    rootEncryptedKeysRef.current = encryptedKeys;
    const currentUserWrapped = encryptedKeys[currentUserId];
    if (!currentUserWrapped) {
      throw new Error(
        'Current user has no wrapped root key — encryption keys not set up.'
      );
    }
    currentUserRootWrappedRef.current = currentUserWrapped;
    dispatch({ type: 'UPDATE_ROW', id: rootItem.id, state: 'staged' });

    // Mint a symmetric key for every nested folder in the effective
    // scope, wrapped by its parent folder's key. Inner encryption roots
    // (and everything under them) are excluded — stacked encryption
    // leaves those subtrees with their existing keys. Processed top-down
    // so each folder's chain only references already-minted ancestors.
    // Serial because later entries depend on earlier ones.
    const innerRoots = innerEncryptionRoots(flat, rootItem.id);
    const nestedFolders = foldersOnly(flat)
      .filter(
        n => n.item.id !== rootItem.id && !isInsideInnerRoot(n, innerRoots)
      )
      .sort((a, b) => a.depth - b.depth);
    for (const folder of nestedFolders) {
      if (signal.aborted) throw abortError();
      dispatch({ type: 'UPDATE_ROW', id: folder.item.id, state: 'running' });
      const chain = chainForNode(
        folder,
        rootItem.id,
        folderWrappedKeysRef.current
      );
      const { wrappedKey } = await vaultClient.encryptWithKey(
        new ArrayBuffer(0),
        currentUserWrapped,
        chain
      );
      folderWrappedKeysRef.current.set(folder.item.id, wrappedKey);
      dispatch({ type: 'UPDATE_ROW', id: folder.item.id, state: 'staged' });
    }
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
        folderWrappedKeysRef,
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
  folderWrappedKeysRef: React.MutableRefObject<Map<string, ArrayBuffer>>;
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
  folderWrappedKeysRef,
  signal,
  dispatch,
  onFileStaged,
}: StageOneEncryptArgs): Promise<void> {
  const node = flat.find(n => n.item.id === targetId);
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
      // Chain is the wrapped keys of every intermediate folder between the
      // root (exclusive) and this file's direct parent (inclusive). The
      // vault resolves the chain to the direct parent's key, mints K_file,
      // encrypts content with K_file, and wraps K_file with the direct
      // parent's key.
      const chain = chainForNode(
        node,
        rootItem.id,
        folderWrappedKeysRef.current
      );
      const { encryptedData, wrappedKey: wk } =
        await vaultClient.encryptWithKey(plaintext, entryKey, chain);
      encryptedContent = encryptedData;
      wrappedKey = wk;
    }

    const newFilename = stagedFilename(node.item.title);
    const uploadUrl = await getEncryptionUploadUrl(
      targetId,
      newFilename,
      signal
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
  rootItem: Item;
  flat: FlatNode[];
  processableIds: string[];
  signal: AbortSignal;
  dispatch: DispatchFn;
  onFileStaged: (id: string, staged: { newFilename: string }) => void;
};

async function decryptPipeline({
  vaultClient,
  rootItem,
  flat,
  processableIds,
  signal,
  dispatch,
  onFileStaged,
}: DecryptPipelineArgs): Promise<void> {
  // Folders (and the root itself, if it's a folder) have no per-item
  // decrypt work — their encryption state is cleared by the backend in
  // a single commit — but they still need to visually progress from
  // 'pending' to 'staged' → 'done' alongside the files. Mark them now.
  // Skipped rows (inner roots and plaintext descendants) are NOT
  // promoted because UPDATE_ROW would overwrite their 'skipped' state;
  // we filter to the in-scope items.
  const innerRoots = innerEncryptionRoots(flat, rootItem.id);
  const processableIdsSet = new Set(processableIds);
  for (const node of flat) {
    if (processableIdsSet.has(node.item.id)) continue;
    if (node.item.type !== ItemType.FOLDER) continue;
    if (isInsideInnerRoot(node, innerRoots)) continue;
    // Only promote in-scope folders that would have been 'pending'
    // (encrypted, not inside an inner root).
    if (!node.item.is_encrypted) continue;
    dispatch({ type: 'UPDATE_ROW', id: node.item.id, state: 'staged' });
  }

  const queue = [...processableIds];
  const worker = async (): Promise<void> => {
    while (queue.length > 0) {
      if (signal.aborted) throw abortError();
      const id = queue.shift();
      if (!id) return;

      const node = flat.find(n => n.item.id === id);
      if (!node) continue;

      dispatch({ type: 'UPDATE_ROW', id, state: 'running' });

      try {
        const driver = getDriver();
        const keyChain = await driver.getKeyChain(id);
        const entryKey = fromBase64(keyChain.encrypted_key_for_user);
        const chain = keyChain.chain.map(e =>
          fromBase64(e.encrypted_symmetric_key)
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
          chain.length > 0 ? chain : undefined
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
