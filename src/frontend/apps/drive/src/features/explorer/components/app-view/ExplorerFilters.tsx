import {
  FileIcon,
  Filter,
  FilterOption,
  IconSize,
  SearchFilter,
  SearchUserItem,
} from "@gouvfr-lasuite/ui-kit";
import { DateRangePicker } from "@gouvfr-lasuite/cunningham-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import folderIcon from "@/assets/folder/folder.svg";
import mimeOther from "@/assets/files/icons/mime-other.svg";
import { Key } from "react-aria-components";
import { useAppExplorer } from "./AppExplorer";
import { ItemType, UserLight } from "@/features/drivers/types";
import { ItemFilters, ItemFiltersScope } from "@/features/drivers/Driver";
import { useItems } from "../../hooks/useQueries";
import { useContacts, useUsers } from "@/features/users/hooks/useUserQueries";
import { DatePreset, DateRange, presetRange } from "../../utils/dateFilters";
import { TFunction } from "i18next";
import { ItemIcon } from "../icons/ItemIcon";
import { getItemTitle } from "../../utils/utils";
import { useAuth } from "@/features/auth/Auth";

const ALL = "all";

export const handleFilterChange = (
  filters: ItemFilters = {},
  name: string,
  value: Key | null,
) => {
  if (value === ALL) {
    const newFilters = { ...filters };
    delete newFilters[name as keyof ItemFilters];
    return newFilters;
  } else {
    return { ...filters, [name]: value };
  }
};

const getResetOption = (t: TFunction) => {
  return {
    label: t("explorer.filters.type.options.reset"),
    render: () => (
      <div className="explorer__filters__item">
        <span className="material-icons">undo</span>
        {t("explorer.filters.type.options.reset")}
      </div>
    ),
    value: ALL,
  };
};

export const ExplorerFilters = () => {
  const { filters, onFiltersChange } = useAppExplorer();
  const { user } = useAuth();

  const onChange = (name: string, value: Key | null) => {
    onFiltersChange?.(handleFilterChange(filters, name, value));
  };

  // The modification date filter drives two query params at once.
  const onModifiedChange = (range: DateRange | null) => {
    const newFilters = { ...filters };
    delete newFilters.updated_at_after;
    delete newFilters.updated_at_before;
    onFiltersChange?.({ ...newFilters, ...(range ?? {}) });
  };

  return (
    <div className="explorer__filters">
      <ExplorerFilterCategory
        value={filters?.category ?? null}
        onChange={(value) => onChange("category", value)}
      />
      {/* Contacts and user search both require authentication. */}
      {user && (
        <ExplorerFilterContact
          value={filters?.contact ?? null}
          onChange={(value) => onChange("contact", value ?? ALL)}
        />
      )}
      <ExplorerFilterModified onChange={onModifiedChange} />
    </div>
  );
};

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

// A representative mimetype per category, resolved to an icon by the ui-kit's
// getMimeCategory so filter options match the icons shown on items.
const CATEGORY_OPTIONS: { value: string; mimetype: string }[] = [
  { value: "doc", mimetype: "application/vnd.oasis.opendocument.text" },
  { value: "powerpoint", mimetype: "application/vnd.oasis.opendocument.presentation" },
  { value: "calc", mimetype: "application/vnd.oasis.opendocument.spreadsheet" },
  { value: "pdf", mimetype: "application/pdf" },
  { value: "image", mimetype: "image/png" },
  { value: "video", mimetype: "video/mp4" },
  { value: "audio", mimetype: "audio/mpeg" },
  { value: "archive", mimetype: "application/zip" },
  { value: "other", mimetype: "text/plain" },
];

export const ExplorerFilterCategory = (props: {
  value: string | null;
  onChange: (value: Key | null) => void;
}) => {
  const { t } = useTranslation();

  const options: FilterOption[] = useMemo(
    () => [
      // Reset sits at the top of the list, above the categories, as in the design.
      { ...getResetOption(t), showSeparator: true },
      ...CATEGORY_OPTIONS.map(({ value, mimetype }) => ({
        label: t(`explorer.filters.category.options.${value}`),
        value,
        render: () => (
          <div className="explorer__filters__item">
            <FileIcon file={{ mimetype, title: "" }} size={IconSize.SMALL} />
            {t(`explorer.filters.category.options.${value}`)}
          </div>
        ),
      })),
    ],
    [t],
  );

  return (
    <Filter
      label={t("explorer.filters.category.label")}
      options={options}
      selectedKey={props.value ?? null} // undefined would trigger "uncontrolled components become controlled" warning.
      onSelectionChange={props.onChange}
    />
  );
};

const MODIFIED_PRESETS: DatePreset[] = [
  "today",
  "last_7_days",
  "last_30_days",
  "this_year",
];
const MODIFIED_CUSTOM = "custom";

export const ExplorerFilterModified = (props: {
  onChange: (range: DateRange | null) => void;
}) => {
  const { t } = useTranslation();
  const [preset, setPreset] = useState<Key | null>(null);
  const [isCustom, setIsCustom] = useState(false);

  const options: FilterOption[] = useMemo(
    () => [
      { ...getResetOption(t), showSeparator: true },
      ...MODIFIED_PRESETS.map((value) => ({
        label: t(`explorer.filters.modified.options.${value}`),
        value,
        render: () => (
          <div className="explorer__filters__item">
            {t(`explorer.filters.modified.options.${value}`)}
          </div>
        ),
      })),
      {
        label: t("explorer.filters.modified.options.custom"),
        value: MODIFIED_CUSTOM,
        render: () => (
          <div className="explorer__filters__item">
            {t("explorer.filters.modified.options.custom")}
          </div>
        ),
      },
    ],
    [t],
  );

  const onSelectionChange = (key: Key | null) => {
    if (key === ALL) {
      setPreset(null);
      setIsCustom(false);
      props.onChange(null);
      return;
    }
    if (key === MODIFIED_CUSTOM) {
      setPreset(key);
      setIsCustom(true);
      return;
    }
    setPreset(key);
    setIsCustom(false);
    props.onChange(presetRange(key as DatePreset));
  };

  return (
    <>
      <Filter
        label={t("explorer.filters.modified.label")}
        options={options}
        selectedKey={preset}
        onSelectionChange={onSelectionChange}
      />
      {isCustom && (
        <DateRangePicker
          compact
          hideLabel
          startLabel={t("explorer.filters.modified.start")}
          endLabel={t("explorer.filters.modified.end")}
          onChange={(range) =>
            // The picker emits ISO datetimes; the backend wants date-only bounds.
            props.onChange(
              range
                ? {
                    updated_at_after: range[0].slice(0, 10),
                    updated_at_before: range[1].slice(0, 10),
                  }
                : null,
            )
          }
        />
      )}
    </>
  );
};

export const ExplorerFilterType = (props: {
  value: ItemType | null;
  onChange: (value: Key | null) => void;
}) => {
  const { t } = useTranslation();

  const typeOptions: FilterOption[] = useMemo(
    () => [
      {
        label: t("explorer.filters.type.options.folder"),
        value: "folder",
        render: () => (
          <div className="explorer__filters__item">
            <img src={folderIcon.src} alt="" width="24" height="24" />
            {t("explorer.filters.type.options.folder")}
          </div>
        ),
      },
      {
        label: t("explorer.filters.type.options.file"),
        render: () => (
          <div className="explorer__filters__item">
            <img src={mimeOther.src} alt="" width="24" height="24" />
            {t("explorer.filters.type.options.file")}
          </div>
        ),
        value: "file",
        showSeparator: true,
      },
      getResetOption(t),
    ],
    [t],
  );

  return (
    <Filter
      label={t("explorer.filters.type.label")}
      options={typeOptions}
      selectedKey={props.value ?? null} // undefined would trigger "uncontrolled components become controlled" warning.
      onSelectionChange={props.onChange}
    />
  );
};

export const ExplorerFilterWorkspace = (props: {
  value: string | null;
  onChange: (value: Key | null) => void;
  isDisabled?: boolean;
}) => {
  const { t } = useTranslation();
  const { data: items } = useItems();

  const options = useMemo(() => {
    return [
      ...(items?.map((item) => ({
        label: item.title,
        value: item.id,
        render: () => (
          <div className="explorer__filters__item">
            <ItemIcon item={item} size={IconSize.SMALL} />
            {getItemTitle(item)}
          </div>
        ),
      })) ?? []),
      getResetOption(t),
    ];
  }, [items]);

  if (!options) {
    return null;
  }

  return (
    <Filter
      label={t("explorer.filters.folders.label")}
      options={options}
      selectedKey={props.value ?? null} // undefined would trigger "uncontrolled components become controlled" warning.
      onSelectionChange={props.onChange}
      isDisabled={props.isDisabled}
    />
  );
};

export const ExplorerFilterScope = (props: {
  value: string | null;
  onChange: (value: Key | null) => void;
}) => {
  const { t } = useTranslation();

  const options: FilterOption[] = useMemo(
    () => [
      {
        label: t("explorer.filters.scopes.options.trash"),
        value: ItemFiltersScope.DELETED,
        render: () => (
          <div className="explorer__filters__item">
            {t("explorer.filters.scopes.options.trash")}
          </div>
        ),
        showSeparator: true,
      },
      getResetOption(t),
    ],
    [t],
  );

  return (
    <Filter
      label={t("explorer.filters.scopes.label")}
      options={options}
      selectedKey={props.value ?? null} // undefined would trigger "uncontrolled components become controlled" warning.
      onSelectionChange={props.onChange}
    />
  );
};
