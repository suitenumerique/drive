import {
  Access,
  Invitation,
  Item,
  ItemType,
  LinkReach,
  LinkRole,
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
} from "@/features/explorer/hooks/useMutationsAccesses";
import { useMutationUpdateLinkConfiguration } from "@/features/explorer/hooks/useMutations";
import {
  useInfiniteItemInvitations,
  useItem,
  useItemAccesses,
} from "@/features/explorer/hooks/useQueries";
import { useUsers } from "@/features/users/hooks/useUserQueries";
import { useClipboard } from "@/hooks/useCopyToClipboard";
import {
  HorizontalSeparator,
  ShareModal,
  ShareModalCopyLinkFooter,
} from "@gouvfr-lasuite/ui-kit";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/router";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

type WorkspaceShareModalProps = {
  isOpen: boolean;
  onClose: () => void;
  item: Item;
};

export const ItemShareModal = ({
  isOpen,
  onClose,
  item: initialItem,
}: WorkspaceShareModalProps) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const copyToClipboard = useClipboard();
  const itemId = initialItem.originalId ?? initialItem.id;
  const { data: item } = useItem(itemId, {
    enabled: isOpen,
    initialData: initialItem,
  });

  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [queryValue, setQueryValue] = useState("");
  const previousSearchResult = useRef<User[]>([]);
  const { data } = useItemAccesses(itemId);

  const { data: invitations, hasNextPage: hasNextInvitations } =
    useInfiniteItemInvitations(itemId);
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
    [t],
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
    },
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
        itemId: itemId,
        userId: user.id,
        role: role as Role,
      }),
    );

    const promisesInvitation = inviteByEmail.map((user) =>
      createInvitation({
        itemId: itemId,
        email: user.email,
        role: role as Role,
      }),
    );

    await Promise.all([...promises, ...promisesInvitation]);

    queryClient.invalidateQueries({
      queryKey: ["itemAccesses", itemId],
    });

    queryClient.invalidateQueries({
      queryKey: ["itemInvitations", itemId],
    });
  };

  const accessesData: Access[] = useMemo(() => {
    if (!data) {
      return [];
    }

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
      const result = {
        ...access,
        can_delete: access.abilities.destroy,
      };
      if (!access.max_ancestors_role) {
        return result;
      }

      // Only search for parent if max_ancestors_role is different from max_role
      if (access.max_ancestors_role === access.max_role) {
        return result;
      }

      return {
        ...result,
        parent_id_max_role: access.max_ancestors_role_item_id,
      };
    });
  }, [data]);

  const invitationsData: Invitation[] = useMemo(() => {
    if (!invitations) {
      return [];
    }

    return invitations.pages.flatMap((page) => page.results);
  }, [invitations]);

  const ownerCount = useMemo(() => {
    return accessesData.filter((access) => access.max_role === Role.OWNER)
      .length;
  }, [accessesData]);

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
    const options = item?.abilities.link_select_options;
    const availableReaches = options ? Object.keys(options) : [];

    return Object.values(LinkReach).map((reach) => {
      const isAvailable = availableReaches.includes(reach);
      return {
        value: reach,
        label: t(`share_modal.options.link_reach.${reach}`),
        isDisabled: !isAvailable,
      };
    });
  }, [item, t]);

  const linkRoleChoices = useMemo(() => {
    const options = item?.abilities.link_select_options;

    if (!options) {
      return Object.values(LinkRole).map((role) => ({
        value: role,
        label: t(`roles.${role}`),
        subText: t(`share_modal.options.subtext.${role}`),
        isDisabled: true,
      }));
    }

    const currentLinkReach = item?.computed_link_reach;
    if (!currentLinkReach) {
      return Object.values(LinkRole).map((role) => ({
        value: role,
        label: t(`roles.${role}`),
        subText: t(`share_modal.options.subtext.${role}`),
        isDisabled: true,
      }));
    }

    const linkRoleOptions = options[currentLinkReach];
    const availableRoles = linkRoleOptions || [];

    if (availableRoles.length === 0) {
      return [];
    }

    return Object.values(LinkRole).map((role) => ({
      value: role,
      label: t(`roles.${role}`),
      subText: t(`share_modal.options.subtext.${role}`),
      isDisabled: !availableRoles.includes(role),
    }));
  }, [item, t]);

  const parentItemId = useMemo(() => {
    const pathParts = item?.path.split(".");
    if (!pathParts) {
      return undefined;
    }
    return pathParts[pathParts.length - 2];
  }, [item]);

  const linkReachTopMessage = useMemo(() => {
    const hasDisabled = linkReachChoices.some((reach) => reach.isDisabled);
    if (hasDisabled && parentItemId) {
      return <RedirectionToParentItem itemId={parentItemId} />;
    }
    return undefined;
  }, [linkReachChoices, parentItemId]);

  const linkRoleTopMessage = useMemo(() => {
    const hasDisabled = linkRoleChoices.some((role) => role.isDisabled);
    if (hasDisabled && parentItemId) {
      return <RedirectionToParentItem itemId={parentItemId} />;
    }
    return undefined;
  }, [linkRoleChoices, parentItemId]);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const updateLinkConfiguration = useMutationUpdateLinkConfiguration();

  return (
    <ShareModal
      isOpen={isOpen}
      loading={isLoadingUsers ?? false}
      onClose={onClose}
      aria-label="Share modal"
      modalTitle={t("explorer.actions.share.modal.title")}
      canUpdate={item?.abilities.accesses_manage}
      canView={item?.abilities.accesses_view}
      accesses={accessesData}
      invitations={invitationsData}
      invitationRoles={rolesOptions}
      onDeleteAccess={(access) =>
        deleteAccess({
          itemId: itemId,
          accessId: access.id,
        })
      }
      onDeleteInvitation={(invitation) =>
        deleteInvitation({
          itemId: itemId,
          invitationId: invitation.id,
        })
      }
      onUpdateInvitation={(invitation, role) =>
        updateInvitation({
          itemId: itemId,
          invitationId: invitation.id,
          role: role as Role,
        })
      }
      onUpdateAccess={(access, role) => {
        // TODO: This should be added in the ui kit directly?
        if (role === access.role) {
          return;
        }

        if (!access.is_explicit) {
          onInviteUser([access.user], role as Role);
        } else {
          updateAccess({
            itemId: itemId,
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
        if (
          access.max_ancestors_role_item_id &&
          access.max_ancestors_role_item_id !== itemId
        ) {
          return (
            <RedirectionToParentItem
              itemId={access.max_ancestors_role_item_id}
            />
          );
        }

        if (
          ownerCount === 1 &&
          availableRoles.length === 0 &&
          access.role === Role.OWNER
        ) {
          return t("share_modal.options.top_message.only_owner");
        }
        if (availableRoles.length === 0 && access.role !== Role.OWNER) {
          return t("share_modal.options.top_message.to_lower_role");
        }
        return undefined;
      }}
      getAccessRoles={(access) => {
        const availableRoles = access.abilities.set_role_to;

        const isDisabled = (role: Role) => {
          return !availableRoles.includes(role) && access.role !== role;
        };

        return [
          {
            value: Role.READER,
            subText: t("share_modal.options.subtext.reader"),
            isDisabled: isDisabled(Role.READER),
            label: t("roles.reader"),
          },
          {
            value: Role.EDITOR,
            subText: t("share_modal.options.subtext.editor"),
            isDisabled: isDisabled(Role.EDITOR),
            label: t("roles.editor"),
          },
          {
            value: Role.ADMIN,
            subText: t("share_modal.options.subtext.admin"),
            isDisabled: isDisabled(Role.ADMIN),
            label: t("roles.administrator"),
          },
          {
            value: Role.OWNER,
            subText: t("share_modal.options.subtext.owner"),
            isDisabled: isDisabled(Role.OWNER),
            label: t("roles.owner"),
          },
        ];
      }}
      outsideSearchContent={
        <ShareModalCopyLinkFooter
          onCopyLink={() => {
            if (item?.type === ItemType.FILE) {
              copyToClipboard(
                `${window.location.origin}/explorer/items/files/${itemId}`,
              );
            } else {
              copyToClipboard(
                `${window.location.origin}/explorer/items/${itemId}`,
              );
            }
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
      showLinkRole={true}
      linkReach={item?.computed_link_reach ?? item?.link_reach}
      linkRole={item?.computed_link_role ?? item?.link_role}
      topLinkReachMessage={linkReachTopMessage}
      topLinkRoleMessage={linkRoleTopMessage}
      onUpdateLinkRole={(value) => {
        updateLinkConfiguration.mutate({
          itemId: itemId,
          link_reach:
            item?.computed_link_reach ??
            item?.link_reach ??
            LinkReach.RESTRICTED,
          link_role: value as LinkRole,
        });
      }}
      onUpdateLinkReach={(value) => {
        const linkRole =
          value === LinkReach.RESTRICTED
            ? undefined
            : (item?.computed_link_role ?? item?.link_role ?? LinkRole.READER);
        updateLinkConfiguration.mutate({
          itemId: itemId,
          link_reach: value as LinkReach,
          link_role: linkRole,
        });
      }}
    >
      {!item?.abilities.accesses_manage && <HorizontalSeparator />}
    </ShareModal>
  );
};

const RedirectionToParentItem = ({ itemId }: { itemId: string }) => {
  const { t } = useTranslation();
  const router = useRouter();

  return (
    <div>
      {t("share_modal.options.top_message.inherited_edit")}{" "}
      <button
        type="button"
        className="workspace-share-modal__parent-folder-link"
        onClick={() => {
          router.push(`/explorer/items/${itemId}`);
        }}
      >
        {t("share_modal.options.top_message.parent_folder")}
      </button>
    </div>
  );
};
