import { getDriver } from "@/features/config/Config";
import { useMutation } from "@tanstack/react-query";
import { useOnSuccessAccessOrInvitationMutation } from "./useRefreshItems";

// ============================================================================
// ACCESS & INVITATION MUTATIONS
// ============================================================================

export const useMutationCreateAccess = () => {
  const driver = getDriver();
  const onSuccessAccessOrInvitation = useOnSuccessAccessOrInvitationMutation();
  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.createAccess>) => {
      return driver.createAccess(...payload);
    },
    onSuccess: (_, variables) => {
      onSuccessAccessOrInvitation(variables.itemId, false);
    },
  });
};

export const useMutationCreateInvitation = () => {
  const driver = getDriver();
  const onSuccessAccessOrInvitation = useOnSuccessAccessOrInvitationMutation();

  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.createInvitation>) => {
      return driver.createInvitation(...payload);
    },
    onSuccess: (_, variables) => {
      onSuccessAccessOrInvitation(variables.itemId, true);
    },
  });
};

export const useMutationUpdateInvitation = () => {
  const driver = getDriver();

  const onSuccessAccessOrInvitation = useOnSuccessAccessOrInvitationMutation();
  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.updateInvitation>) => {
      return driver.updateInvitation(...payload);
    },
    onSuccess: (_, variables) => {
      onSuccessAccessOrInvitation(variables.itemId, true);
    },
  });
};

export const useMutationUpdateAccess = () => {
  const driver = getDriver();
  const onSuccessAccessOrInvitation = useOnSuccessAccessOrInvitationMutation();
  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.updateAccess>) => {
      return driver.updateAccess(...payload);
    },
    onSuccess: (_data, variables) => {
      onSuccessAccessOrInvitation(variables.itemId, false);
    },
  });
};

export const useMutationDeleteAccess = () => {
  const driver = getDriver();
  const onSuccessAccessOrInvitation = useOnSuccessAccessOrInvitationMutation();
  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.deleteAccess>) => {
      return driver.deleteAccess(...payload);
    },
    onSuccess: (_, variables) => {
      onSuccessAccessOrInvitation(variables.itemId, false);
    },
  });
};

export const useMutationAcceptEncryptionAccess = () => {
  const driver = getDriver();
  const onSuccessAccessOrInvitation = useOnSuccessAccessOrInvitationMutation();
  return useMutation({
    mutationFn: (
      payload: {
        itemId: string;
        accessId: string;
        encrypted_item_symmetric_key_for_user: string;
        encryption_public_key_fingerprint: string;
      },
    ) => {
      return driver.acceptEncryptionAccess(
        payload.itemId,
        payload.accessId,
        {
          encrypted_item_symmetric_key_for_user:
            payload.encrypted_item_symmetric_key_for_user,
          encryption_public_key_fingerprint:
            payload.encryption_public_key_fingerprint,
        },
      );
    },
    onSuccess: (_data, variables) => {
      onSuccessAccessOrInvitation(variables.itemId, false);
    },
  });
};

export const useMutationDeleteInvitation = () => {
  const driver = getDriver();
  const onSuccessAccessOrInvitation = useOnSuccessAccessOrInvitationMutation();
  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.deleteInvitation>) => {
      return driver.deleteInvitation(...payload);
    },
    onSuccess: (_, variables) => {
      onSuccessAccessOrInvitation(variables.itemId, true);
    },
  });
};
