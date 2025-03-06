import { useQuery } from "@tanstack/react-query";
import { getDriver } from "@/features/config/config";
import { Button } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
export const ExplorerTree = () => {
  const { t } = useTranslation();
  const driver = getDriver();
  console.log("ExplorerTree", driver);
  const { data } = useQuery({
    queryKey: ["explorer-tree"],
    queryFn: () => driver.getItems(),
  });
  console.log("ExplorerTree", data);

  return (
    <div>
      <div className="explorer__tree__actions">
        <div className="explorer__tree__actions__left">
          <Button icon={<span className="material-icons">add</span>}>
            {t("explorer.tree.createFolder")}
          </Button>
          <Button color="secondary">{t("explorer.tree.import")}</Button>
        </div>
        <Button
          color="primary-text"
          aria-label={t("explorer.tree.search")}
          icon={<span className="material-icons">search</span>}
        ></Button>
      </div>
      <h4>Explorer Tree</h4>
      <div>
        {data?.map((item) => (
          <div key={item.id}>{item.name}</div>
        ))}
      </div>
    </div>
  );
};
