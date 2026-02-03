import { useEffect, useState } from "react";
import { ReleaseNoteModal } from "@gouvfr-lasuite/ui-kit";
import { useTranslation } from "react-i18next";

import { useConfig } from "@/features/config/ConfigProvider";

import { useReleaseNote } from "./useReleaseNote";

export const ReleaseNoteAuto = () => {
  const { config } = useConfig();
  const { t } = useTranslation();
  const enabled = config?.FRONTEND_RELEASE_NOTE_ENABLED;
  const [isOpen, setIsOpen] = useState(false);
  const { shouldShow, mainTitle, steps, markAsSeen } = useReleaseNote();

  useEffect(() => {
    if (shouldShow) {
      setIsOpen(true);
    }
  }, [shouldShow]);

  const handleClose = async () => {
    setIsOpen(false);
    await markAsSeen();
  };

  if (!enabled) {
    return null;
  }

  if (!shouldShow && !isOpen) {
    return null;
  }

  return (
    <ReleaseNoteModal
      isOpen={isOpen}
      appName={t("release_notes.labels.app_name")}
      mainTitle={mainTitle}
      steps={steps}
      footerLink={{
        label: t("release_notes.labels.see_whats_new"),
        href: "https://docs.numerique.gouv.fr/docs/46085eec-8fd9-4466-98db-b8a40fb545fd/",
      }}
      onClose={handleClose}
      onComplete={handleClose}
    />
  );
};
