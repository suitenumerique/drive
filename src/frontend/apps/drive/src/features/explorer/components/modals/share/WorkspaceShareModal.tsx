import {
  Access,
  Invitation,
  Item,
  LinkReach,
  Role,
  User,
} from "@/features/drivers/types";
import {
  useMutationCreateAccess,
  useMutationCreateInvitation,
  useMutationDeleteAccess,
  useMutationDeleteInvitation,
  useMutationUpdateAccess,
  useMutationUpdateInvitation,
  useMutationUpdateItem,
} from "@/features/explorer/hooks/useMutations";
import {
  useInfiniteItemInvitations,
  useItemAccesses,
} from "@/features/explorer/hooks/useQueries";
import { useUsers } from "@/features/users/hooks/useUserQueries";
import { useClipboard } from "@/hooks/useCopyToClipboard";
import {
  HorizontalSeparator,
  ShareModal,
  ShareModalCopyLinkFooter,
  useTreeContext,
} from "@gouvfr-lasuite/ui-kit";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
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
  const treeContext = useTreeContext<Item>();
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [queryValue, setQueryValue] = useState("");
  const previousSearchResult = useRef<User[]>([]);
  const { data } = useItemAccesses(item.id);

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

  /**
   * Keep previous search result when changing the query value to avoid flickering
   * Because when it's the first time we have this value, the queryKey changes and by default react-query returns undefined
   */
  const { data: users, isLoading: isLoadingUsers } = useUsers(
    { q: queryValue },
    {
      enabled: queryValue !== undefined && queryValue !== "",
      placeholderData: (previousData) => previousData,
    }
  );

  // Used for the initial data
  useEffect(() => {
    if (users) {
      previousSearchResult.current = users;
    } else {
      previousSearchResult.current = [];
    }
  }, [users]);

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

    // return data;

    const accessesByUserId = new Map<string, Access>();

    data.forEach((access) => {
      const existing = accessesByUserId.get(access.user.id);

      if (!existing) {
        accessesByUserId.set(access.user.id, access);
        return;
      }

      if (!existing.is_explicit && access.is_explicit) {
        accessesByUserId.set(access.user.id, access);
      }
    });

    const result = Array.from(accessesByUserId.values());

    // return result;
    // Find parent_id_max_role for each access
    return result.map((access) => {
      if (!access.max_ancestors_role) {
        return access;
      }

      // Only search for parent if max_ancestors_role is different from max_role
      if (access.max_ancestors_role === access.max_role) {
        return access;
      }

      // Find the access with max_role equal to max_ancestors_role and same user/team
      const parentAccess = data.find((candidateAccess) => {
        const sameUser =
          access.user?.id && candidateAccess.user?.id
            ? access.user.id === candidateAccess.user.id
            : false;
        const sameTeam =
          access.team && candidateAccess.team
            ? access.team === candidateAccess.team
            : false;

        return (
          (sameUser || sameTeam) &&
          candidateAccess.max_role === access.max_ancestors_role
        );
      });

      return {
        ...access,
        parent_id_max_role: parentAccess?.item.id,
      };
    });
  }, [data]);

  console.log("ACCESSES DATA", accessesData);

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

  const linkReachChoices = useMemo(() => {
    const options = item.abilities.link_select_options;
    if (!options) {
      return [];
    }

    return Object.entries(options).map(([key]) => ({
      value: key as LinkReach,

      label: t(`share_modal.options.link_reach.${key}`),
    }));
  }, [item]);

  const linkRoleChoices = useMemo(() => {
    const options = item.abilities.link_select_options;

    if (!options) {
      return [];
    }

    const currentLinkReach = item.computed_link_reach;
    if (!currentLinkReach) {
      return undefined;
    }

    const linkRoleOptions = options[currentLinkReach];
    console.log("AAAAAA", currentLinkReach, options);

    if (!linkRoleOptions) {
      return undefined;
    }

    return linkRoleOptions.map((role) => ({
      value: role,
      label: t(`roles.${role}`),
    }));
  }, [item]);

  const updateItem = useMutationUpdateItem();

  return (
    <ShareModal
      isOpen={isOpen}
      loading={isLoadingUsers ?? false}
      onClose={onClose}
      modalTitle={t("explorer.actions.share.modal.title")}
      canUpdate={item.abilities?.accesses_manage}
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
      onUpdateAccess={(access, role) => {
        // TODO: This should be added in the ui kit directly?
        if (role === access.role) {
          return;
        }

        console.log("ACCESS", access);
        if (!access.is_explicit) {
          onInviteUser([access.user], role as Role);
        } else {
          updateAccess({
            itemId: item.id,
            accessId: access.id,
            role: role as Role,
            user_id: access.user.id,
          });
        }
      }}
      onSearchUsers={onSearch}
      hasNextMembers={false}
      hasNextInvitations={hasNextInvitations}
      searchUsersResult={queryValue === "" ? undefined : users}
      onInviteUser={(users, role) => onInviteUser(users, role as Role)}
      accessRoleTopMessage={(access) => {
        const availableRoles = access.abilities.set_role_to;
        if (availableRoles.length === 0 && access.role === Role.OWNER) {
          return t("share_modal.options.top_message.only_owner");
        }
        if (availableRoles.length === 0 && access.role !== Role.OWNER) {
          return t("share_modal.options.top_message.to_lower_role");
        }
        return undefined;
      }}
      getAccessRoles={(access) => {
        const availableRoles = access.abilities.set_role_to;
        // const availableRoles = [Role.EDITOR, Role.ADMIN, Role.OWNER];

        const isDisabled = (role: Role) => {
          return !availableRoles.includes(role) && access.role !== role;
        };

        return [
          {
            value: Role.READER,
            subtText: t("share_modal.options.subtext.reader"),
            isDisabled: isDisabled(Role.READER),
            label: t("roles.reader"),
          },
          {
            value: Role.EDITOR,
            subtText: t("share_modal.options.subtext.editor"),
            isDisabled: isDisabled(Role.EDITOR),
            label: t("roles.editor"),
          },
          {
            value: Role.ADMIN,
            subtText: t("share_modal.options.subtext.admin"),
            isDisabled: isDisabled(Role.ADMIN),
            label: t("roles.administrator"),
          },
          {
            value: Role.OWNER,
            subtText: t("share_modal.options.subtext.owner"),
            isDisabled: isDisabled(Role.OWNER),
            label: t("roles.owner"),
          },
        ];
      }}
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
      linkSettings={true}
      accessRoleKey="max_role"
      linkReachChoices={linkReachChoices}
      linkRoleChoices={linkRoleChoices}
      linkReach={item.computed_link_reach ?? item.link_reach}
      linkRole={item.computed_link_role ?? item.link_role}
      onUpdateLinkReach={(value) => {
        updateItem.mutate(
          {
            id: item.id,
            link_reach: value as LinkReach,
          },
          {
            onSuccess: () => {
              treeContext?.treeData.updateNode(item.id, {
                link_reach: value as LinkReach,
              });
            },
          }
        );
      }}
      canView={item.abilities?.accesses_view}
    >
      {!item.abilities?.accesses_manage && <HorizontalSeparator />}
    </ShareModal>
  );
};
