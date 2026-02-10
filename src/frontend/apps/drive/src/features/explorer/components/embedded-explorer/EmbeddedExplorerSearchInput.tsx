import { Icon } from "@gouvfr-lasuite/ui-kit";
import { memo } from "react";
import { useTranslation } from "react-i18next";

type EmbeddedExplorerSearchInputProps = {
  onSearch: (query: string) => void;
  value: string;
};

export const EmbeddedExplorerSearchInput = memo(
  (props: EmbeddedExplorerSearchInputProps) => {
    const { t } = useTranslation();

    return (
      <div className="embedded-explorer__search__container">
        <Icon name="search" />
        <input
          type="text"
          placeholder={t(
            "explorer.search.placeholder",
            "Search for a folder..."
          )}
          value={props.value}
          autoFocus={true}
          onChange={(e) => props.onSearch(e.target.value)}
        />
      </div>
    );
  }
);

EmbeddedExplorerSearchInput.displayName = "EmbeddedExplorerSearchInput";
