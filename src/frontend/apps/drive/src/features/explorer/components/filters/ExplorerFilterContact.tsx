import { SearchFilter, SearchUserItem } from "@gouvfr-lasuite/ui-kit";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { UserLight } from "@/features/drivers/types";
import { useContacts, useUsers } from "@/features/users/hooks/useUserQueries";

const CONTACT_RESET = "__contact_reset__";

const contactLabel = (user: UserLight) =>  user.full_name || user.short_name || "";

type ContactItem = { id: string; label: string; user?: UserLight };

export const ExplorerFilterContact = (props: {
  value: string | null;
  onChange: (value: string | null) => void;
}) => {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");

  const isSearching = search.length >= 5;
  const { data: contacts, isLoading: isLoadingContacts } = useContacts({
    enabled: !isSearching,
  });
  const { data: results, isLoading: isLoadingResults } = useUsers(
    { q: search },
    { enabled: isSearching },
  );

  // Below the search threshold, filter the frequent contacts locally so the
  // displayed list always matches what the user typed.
  const users = useMemo(() => {
    if (isSearching) {
      return results ?? [];
    }
    const list = contacts ?? [];
    if (!search) {
      return list;
    }
    const query = search.toLowerCase();
    return list.filter((user) =>
      contactLabel(user).toLowerCase().includes(query),
    );
  }, [isSearching, results, contacts, search]);

  // Derive the active label from the loaded data so it survives a remount,
  // where local state would be lost while the filter value persists. A contact
  // picked through global search and absent from the frequent list still loses
  // its label after a remount; the filter itself stays active.
  const activeContact =
    contacts?.find((user) => user.id === props.value) ??
    results?.find((user) => user.id === props.value);

  // Reset is always present so the list height does not change on selection,
  // which the popover would not recompute (it would clip the last row).
  const items: ContactItem[] = useMemo(() => {
    const userItems = users.map((user) => ({
      id: user.id,
      label: contactLabel(user),
      user,
    }));
    return [
      { id: CONTACT_RESET, label: t("explorer.filters.contact.reset") },
      ...userItems,
    ];
  }, [users, t]);

  const onItemSelect = (item: ContactItem) => {
    props.onChange(item.id === CONTACT_RESET ? null : item.id);
  };

  return (
    <SearchFilter<ContactItem>
      label={t("explorer.filters.contact.label")}
      activeLabel={
        activeContact ? contactLabel(activeContact) : undefined
      }
      isActive={!!props.value}
      placeholder={t("explorer.filters.contact.placeholder")}
      searchValue={search}
      onSearchChange={setSearch}
      items={items}
      isLoading={isSearching ? isLoadingResults : isLoadingContacts}
      emptyState={t("explorer.filters.contact.empty")}
      renderItem={(item) =>
        item.id === CONTACT_RESET ? (
          <div className="explorer__filters__item">
            <span className="material-icons">undo</span>
            {t("explorer.filters.contact.reset")}
          </div>
        ) : (
          <div className="explorer__filters__contact">
            <SearchUserItem user={{ ...item.user!, email: "" }} />
            {item.id === props.value && (
              <span className="material-icons explorer__filters__check">check</span>
            )}
          </div>
        )
      }
      onItemSelect={onItemSelect}
    />
  );
};
