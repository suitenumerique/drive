import { useMemo, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { ReleaseNoteStep } from "@gouvfr-lasuite/ui-kit";

import { useAuth } from "@/features/auth/Auth";
import { fetchAPI } from "@/features/api/fetchApi";
import {
  CURRENT_RELEASE_NOTE,
  CURRENT_VERSION,
  ReleaseNoteConfig,
} from "./releaseNotes.config";

interface UseReleaseNoteResult {
  shouldShow: boolean;
  mainTitle: string;
  steps: ReleaseNoteStep[];
  markAsSeen: () => Promise<void>;
  currentVersion: string;
}

export const useReleaseNote = (): UseReleaseNoteResult => {
  const { t } = useTranslation();
  const { user, refreshUser } = useAuth();

  const shouldShow = useMemo(() => {
    if (!user || !CURRENT_RELEASE_NOTE) {
      return false;
    }
    const isSameVersion = CURRENT_VERSION === user.last_release_note_seen;
    return !isSameVersion;
  }, [user]);

  const mainTitle = useMemo(() => {
    if (!CURRENT_RELEASE_NOTE) {
      return "";
    }
    return t(CURRENT_RELEASE_NOTE.mainTitleKey);
  }, [t]);

  const steps = useMemo((): ReleaseNoteStep[] => {
    if (!CURRENT_RELEASE_NOTE) {
      return [];
    }
    return buildStepsFromConfig(CURRENT_RELEASE_NOTE, t);
  }, [t]);

  const markAsSeen = useCallback(async () => {
    if (!user) {
      return;
    }

    await fetchAPI(`users/${user.id}/`, {
      method: "PATCH",
      body: JSON.stringify({
        last_release_note_seen: CURRENT_VERSION,
      }),
    });

    refreshUser?.();
  }, [user, refreshUser]);

  return {
    shouldShow,
    mainTitle,
    steps,
    markAsSeen,
    currentVersion: CURRENT_VERSION,
  };
};

const buildStepsFromConfig = (
  config: ReleaseNoteConfig,
  t: (key: string) => string,
): ReleaseNoteStep[] => {
  return config.steps.map((step) => ({
    icon: step.icon,
    title: t(step.titleKey),
    description: t(step.descriptionKey),
  }));
};
