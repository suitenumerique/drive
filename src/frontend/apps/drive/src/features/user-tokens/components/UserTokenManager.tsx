import {
  Button as CunninghamButton,
  DataGrid,
  Modal,
  ModalSize,
} from '@openfun/cunningham-react';
import React, { useCallback, useEffect, useState } from 'react';

import { createUserToken, deleteUserToken, listUserTokens } from '../api/index';
import { NewUserToken, UserToken } from '../types';

const formatTimeAgo = (dateString: string) => {
  const now = new Date();
  const date = new Date(dateString);
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  if (seconds < 60) {
    return `${seconds} seconds ago`;
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes} minutes ago`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours} hours ago`;
  }
  const days = Math.floor(hours / 24);
  return `${days} days ago`;
};

// Add id to UserToken type for DataGrid compatibility
interface UserTokenWithId extends UserToken {
  id: string;
}

// Define proper type for DataGrid columns
interface ColumnDef {
  field: string;
  headerName: string;
  width?: number;
  renderCell: (params: { row: UserTokenWithId }) => React.ReactNode;
}

export const UserTokenManager: React.FC = () => {
  const [tokens, setTokens] = useState<UserTokenWithId[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [newToken, setNewToken] = useState<NewUserToken | null>(null);
  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    title: string;
    message: React.ReactNode;
    onConfirm?: () => void;
    confirmText?: string;
    isConfirmation: boolean;
    type?: 'success' | 'error' | 'warning' | 'info';
    size: ModalSize;
  }>({
    isOpen: false,
    title: '',
    message: '',
    isConfirmation: false,
    size: ModalSize.MEDIUM, // Default size using ModalSize enum
  });

  const showNotification = (
    message: string,
    type: 'success' | 'error' = 'success',
    size: ModalSize = ModalSize.SMALL,
  ) => {
    setModalState({
      isOpen: true,
      title: type === 'success' ? 'Success' : 'Error',
      message,
      isConfirmation: false,
      type: type,
      size,
    });
  };

  const showConfirmation = (
    title: string,
    message: React.ReactNode,
    onConfirm: () => void,
    confirmText: string = 'Confirm',
    size: ModalSize = ModalSize.MEDIUM,
  ) => {
    setModalState({
      isOpen: true,
      title,
      message,
      onConfirm,
      confirmText,
      isConfirmation: true,
      size,
    });
  };

  const fetchTokens = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const fetchedTokens = await listUserTokens();
      // Add id to each token
      setTokens(fetchedTokens.map((token) => ({ ...token, id: token.digest })));
    } catch (err) {
      setError(
        'Failed to fetch tokens. Please ensure you are logged in and have permissions.',
      );
      showNotification('Failed to fetch tokens', 'error');
      console.error(err);
    }
    setIsLoading(false);
  }, []);

  useEffect(() => {
    void fetchTokens();
  }, [fetchTokens]);

  const handleCreateToken = async () => {
    setIsLoading(true);
    setError(null);
    setNewToken(null);
    try {
      const generatedToken = await createUserToken();
      setNewToken(generatedToken);
      showNotification(
        'Token created successfully! Store the token key safely, it will not be shown again.',
        'success',
        ModalSize.LARGE,
      );
      void fetchTokens();
    } catch (err) {
      setError('Failed to create token.');
      showNotification('Failed to create token', 'error');
      console.error(err);
    }
    setIsLoading(false);
  };

  const handleDeleteToken = (digest: string) => {
    showConfirmation(
      'Confirm Deletion',
      'Are you sure you want to delete this token?',
      () => {
        void (async () => {
          setIsLoading(true);
          setError(null);
          try {
            await deleteUserToken(digest);
            showNotification('Token deleted successfully!');
            setNewToken(null);
            await fetchTokens();
          } catch (err) {
            setError('Failed to delete token.');
            showNotification('Failed to delete token', 'error');
            console.error(err);
          }
          setIsLoading(false);
        })();
      },
    );
  };

  const columns: ColumnDef[] = [
    {
      field: 'digest',
      headerName: 'Name',
      renderCell: ({ row }: { row: UserTokenWithId }) => <>{row.digest}</>,
    },
    {
      field: 'created',
      headerName: 'Updated at',
      renderCell: ({ row }: { row: UserTokenWithId }) => (
        <>{formatTimeAgo(row.created)}</>
      ),
    },
    {
      field: 'expires',
      headerName: 'Expires at',
      renderCell: ({ row }: { row: UserTokenWithId }) => <>{row.expiry}</>,
    },
    {
      field: 'actions',
      headerName: '',
      width: 50,
      renderCell: ({ row }: { row: UserTokenWithId }) => (
        <CunninghamButton
          onClick={() => {
            handleDeleteToken(row.digest);
          }}
          color="danger"
          size="small"
          icon={<span className="material-icons">delete</span>}
          aria-label="Delete token"
        >
          Delete
        </CunninghamButton>
      ),
    },
  ];

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        paddingTop: 'var(--c--theme--spacing--base, 8px)',
        paddingLeft: 'var(--c--theme--spacing--md, 24px)',
        paddingRight: 'var(--c--theme--spacing--md, 24px)',
        paddingBottom: 'var(--c--theme--spacing--md, 24px)',
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'row',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <h2 style={{ marginBottom: 'var(--c--theme--spacing--medium, 16px)' }}>
          User token management
        </h2>
        <CunninghamButton
          onClick={() => void handleCreateToken()}
          disabled={isLoading}
        >
          {isLoading ? 'Generating...' : 'Generate New Token'}
        </CunninghamButton>
      </div>

      {newToken && (
        <div
          style={{
            background: 'var(--c--theme--colors--success-100)',
            padding: 'var(--c--theme--spacing--md, 24px)',
            borderRadius: '10px',
            marginBottom: 'var(--c--theme--spacing--medium, 16px)',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <span style={{ marginLeft: 16 }}>
            <strong>New Token:</strong> <code>{newToken.token_key}</code>
          </span>
          <span style={{ marginLeft: 16 }}>
            <strong>Digest:</strong> <code>{newToken.digest}</code>
          </span>
          <span style={{ marginLeft: 16 }}>
            <strong>Expires:</strong>{' '}
            <code>{new Date(newToken.expiry).toLocaleString()}</code>
          </span>
        </div>
      )}

      {isLoading && !tokens.length && (
        <div style={{ marginBottom: 'var(--c--theme--spacing--small, 8px)' }}>
          Loading...
        </div>
      )}
      {error && (
        <div
          style={{
            color: 'var(--c--theme--colors--danger-500, red)',
            marginBottom: 'var(--c--theme--spacing--small, 8px)',
          }}
        >
          {error}
        </div>
      )}

      <DataGrid<UserTokenWithId>
        rows={tokens}
        columns={columns}
        isLoading={isLoading}
        emptyCta={<div>No tokens found.</div>}
      />
      {modalState.isOpen && (
        <Modal
          isOpen={modalState.isOpen}
          onClose={() => setModalState((prev) => ({ ...prev, isOpen: false }))}
          title={modalState.title}
          size={modalState.size}
          actions={
            modalState.isConfirmation ? (
              <div
                style={{
                  width: '100%',
                  display: 'flex',
                  flexDirection: 'row',
                  justifyContent: 'space-between',
                }}
              >
                <CunninghamButton
                  onClick={() =>
                    setModalState((prev) => ({ ...prev, isOpen: false }))
                  }
                  color="secondary"
                >
                  Cancel
                </CunninghamButton>
                <CunninghamButton
                  onClick={() => {
                    if (modalState.onConfirm) {
                      modalState.onConfirm();
                    }
                    setModalState((prev) => ({ ...prev, isOpen: false }));
                  }}
                  color="danger"
                >
                  {modalState.confirmText || 'Confirm'}
                </CunninghamButton>
              </div>
            ) : (
              <CunninghamButton
                onClick={() =>
                  setModalState((prev) => ({ ...prev, isOpen: false }))
                }
                color="primary"
              >
                Close
              </CunninghamButton>
            )
          }
        >
          {modalState.message}
        </Modal>
      )}
    </div>
  );
};
