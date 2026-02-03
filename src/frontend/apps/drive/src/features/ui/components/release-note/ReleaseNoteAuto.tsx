import { useEffect, useState } from "react";
import { ReleaseNoteModal } from "@gouvfr-lasuite/ui-kit";

import { useConfig } from "@/features/config/ConfigProvider";

import { useReleaseNote } from "./useReleaseNote";

export const ReleaseNoteAuto = () => {
  const { config } = useConfig();
  const hideReleaseNote = config?.FRONTEND_HIDE_RELEASE_NOTE;
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

  if (hideReleaseNote) {
    return null;
  }

  if (!shouldShow && !isOpen) {
    return null;
  }

  return (
    <ReleaseNoteModal
      isOpen={isOpen}
      appName="Mise à jours de Fichiers"
      mainTitle={mainTitle}
      steps={steps}
      footerLink={{
        label: "Voir les nouveautés",
        href: "https://docs.numerique.gouv.fr/docs/46085eec-8fd9-4466-98db-b8a40fb545fd/",
      }}
      onClose={handleClose}
      onComplete={handleClose}
    />
  );
};
