import { getDriver } from "@/features/config/Config";
import { useMutation, useQueryClient } from "@tanstack/react-query";
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

// ============================================================================
// ASK FOR ACCESS MUTATIONS
// ============================================================================

export const useMutationCreateAskForAccess = () => {
  const driver = getDriver();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.createAskForAccess>) => {
      return driver.createAskForAccess(...payload);
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["itemAskForAccesses", variables.itemId],
      });
    },
  });
};

export const useMutationDeleteAskForAccess = () => {
  const driver = getDriver();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.deleteAskForAccess>) => {
      return driver.deleteAskForAccess(...payload);
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["itemAskForAccesses", variables.itemId],
      });
    },
  });
};

export const useMutationAcceptAskForAccess = () => {
  const driver = getDriver();
  const queryClient = useQueryClient();
  const onSuccessAccessOrInvitation = useOnSuccessAccessOrInvitationMutation();
  return useMutation({
    mutationFn: (...payload: Parameters<typeof driver.acceptAskForAccess>) => {
      return driver.acceptAskForAccess(...payload);
    },
    onSuccess: (_, variables) => {
      onSuccessAccessOrInvitation(variables.itemId, false);
      queryClient.invalidateQueries({
        queryKey: ["itemAskForAccesses", variables.itemId],
      });
    },
  });
};
