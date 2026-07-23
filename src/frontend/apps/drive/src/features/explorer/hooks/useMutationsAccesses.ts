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

export const useMutationBatchShare = () => {
  const driver = getDriver();
  const onSuccessAccessOrInvitation = useOnSuccessAccessOrInvitationMutation();
  return useMutation({
    // Errors are displayed inside the import modal, not by the global toast
    meta: { noGlobalError: true },
    mutationFn: (...payload: Parameters<typeof driver.batchShare>) => {
      return driver.batchShare(...payload);
    },
    onSuccess: (_, variables) => {
      // A batch can create both accesses and invitations
      onSuccessAccessOrInvitation(variables.itemId, false);
      onSuccessAccessOrInvitation(variables.itemId, true);
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
