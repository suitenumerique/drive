import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

type EmbeddedExplorerSearchInputProps = {
  onSearch: (query: string) => void;
};

export const EmbeddedExplorerSearchInput = (
  props: EmbeddedExplorerSearchInputProps
) => {
  const { t } = useTranslation();
  const [inputSearchValue, setInputSearchValue] = useState<string>("");

  const timeoutRef = useRef<NodeJS.Timeout>(null);

  const handleChange = (query: string) => {
    if (query === "") {
      props.onSearch("");
      return;
    }
    setInputSearchValue(query);
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(() => {
      props.onSearch(query);
    }, 300);
  };
  return (
    <div className="embedded-explorer__search">
      <span className="embedded-explorer__search__icon">icone</span>
      <input
        type="text"
        placeholder={t("explorer.search.placeholder", "Rechercher...")}
        value={inputSearchValue}
        onChange={(e) => handleChange(e.target.value)}
      />
    </div>
  );
};
