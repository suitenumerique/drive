import { Access, Invitation, Item, Role, User } from "@/features/drivers/types";
import {
  useMutationCreateAccess,
  useMutationCreateInvitation,
  useMutationDeleteAccess,
  useMutationDeleteInvitation,
  useMutationUpdateAccess,
  useMutationUpdateInvitation,
} from "@/features/explorer/hooks/useMutations";
import {
  useInfiniteItemAccesses,
  useInfiniteItemInvitations,
} from "@/features/explorer/hooks/useQueries";
import { useUsers } from "@/features/users/hooks/useUserQueries";
import { useClipboard } from "@/hooks/useCopyToClipboard";
import { ShareModal, ShareModalCopyLinkFooter } from "@gouvfr-lasuite/ui-kit";
import { useQueryClient } from "@tanstack/react-query";
import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

type WorkspaceShareModalProps = {
  isOpen: boolean;
  onClose: () => void;
  item: Item;
};

export const WorkspaceShareModal = ({
  isOpen,
  onClose,
  item,
}: WorkspaceShareModalProps) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const copyToClipboard = useClipboard();
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [queryValue, setQueryValue] = useState("");
  const { data, hasNextPage: hasNextMembers } = useInfiniteItemAccesses(
    item.id
  );
  const { data: invitations, hasNextPage: hasNextInvitations } =
    useInfiniteItemInvitations(item.id);
  const { mutateAsync: createAccess } = useMutationCreateAccess();
  const { mutateAsync: createInvitation } = useMutationCreateInvitation();

  const { mutateAsync: updateAccess } = useMutationUpdateAccess();
  const { mutateAsync: deleteAccess } = useMutationDeleteAccess();
  const { mutateAsync: deleteInvitation } = useMutationDeleteInvitation();
  const { mutateAsync: updateInvitation } = useMutationUpdateInvitation();

  const rolesOptions = useMemo(
    () =>
      Object.values(Role).map((role) => ({
        label: t(`roles.${role}`),
        value: role,
      })),
    [t]
  );

  const { data: users, isLoading: isLoadingUsers } = useUsers(
    { q: queryValue },
    { enabled: !!queryValue && queryValue !== "" }
  );

  const onInviteUser = async (users: User[], role: Role) => {
    const inviteByEmail = users.filter((user) => user.email === user.id);
    const inviteByUsername = users.filter((user) => user.email !== user.id);

    const promises = inviteByUsername.map((user) =>
      createAccess({
        itemId: item.id,
        userId: user.id,
        role: role as Role,
      })
    );

    const promisesInvitation = inviteByEmail.map((user) =>
      createInvitation({
        itemId: item.id,
        email: user.email,
        role: role as Role,
      })
    );

    await Promise.all(promises);
    await Promise.all(promisesInvitation);

    queryClient.invalidateQueries({
      queryKey: ["itemAccesses", item.id],
    });

    queryClient.invalidateQueries({
      queryKey: ["itemInvitations", item.id],
    });
  };

  const accessesData: Access[] = useMemo(() => {
    if (!data) {
      return [];
    }

    return data.pages.flatMap((page) => page.results);
  }, [data]);

  const invitationsData: Invitation[] = useMemo(() => {
    if (!invitations) {
      return [];
    }

    return invitations.pages.flatMap((page) => page.results);
  }, [invitations]);

  const onSearch = (search: string) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    if (search === "") {
      setQueryValue("");
      return;
    }

    timeoutRef.current = setTimeout(() => {
      setQueryValue(search);
    }, 500);
  };

  return (
    <ShareModal<User, Invitation, Access>
      isOpen={isOpen}
      loading={isLoadingUsers ?? false}
      onClose={onClose}
      modalTitle={t("Share workspace")}
      accesses={accessesData}
      invitations={invitationsData}
      invitationRoles={rolesOptions}
      onDeleteAccess={(access) =>
        deleteAccess({
          itemId: item.id,
          accessId: access.id,
        })
      }
      onDeleteInvitation={(invitation) =>
        deleteInvitation({
          itemId: item.id,
          invitationId: invitation.id,
        })
      }
      onUpdateInvitation={(invitation, role) =>
        updateInvitation({
          itemId: item.id,
          invitationId: invitation.id,
          role: role as Role,
        })
      }
      onUpdateAccess={(access, role) =>
        updateAccess({
          itemId: item.id,
          accessId: access.id,
          role: role as Role,
          user_id: access.user.id,
        })
      }
      onSearchUsers={onSearch}
      hasNextMembers={hasNextMembers}
      hasNextInvitations={hasNextInvitations}
      searchUsersResult={queryValue === "" ? [] : users}
      onInviteUser={(users, role) => onInviteUser(users, role as Role)}
      outsideSearchContent={
        <ShareModalCopyLinkFooter
          onCopyLink={() => {
            copyToClipboard(
              `${window.location.origin}/explorer/items/${item.id}`
            );
          }}
          onOk={() => {
            onClose();
          }}
        />
      }
    />
  );
};
