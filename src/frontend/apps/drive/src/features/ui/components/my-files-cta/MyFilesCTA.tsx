import { DefaultRoute, ORDERED_DEFAULT_ROUTES } from "@/utils/defaultRoutes";
import { Button } from "@gouvfr-lasuite/cunningham-react";
import { Folder } from "@gouvfr-lasuite/ui-kit";
import { useTranslation } from "react-i18next";

export const MyFilesCTA = () => {
  const { t } = useTranslation();
  const myFilesRoute = ORDERED_DEFAULT_ROUTES.find(
    (r) => r.id === DefaultRoute.MY_FILES,
  );
  return (
    <Button variant="secondary" size="small" href={myFilesRoute?.route} icon={<Folder />} data-testid="my-files-cta">
      {t("my_files_cta.my_files")}
    </Button>
  );
};
