import { ReleaseNoteStep } from "@gouvfr-lasuite/ui-kit";

import { ALL_VERSIONS } from "./versions";

export interface ReleaseNoteStepConfig {
  icon: ReleaseNoteStep["icon"];
  activeIcon: ReleaseNoteStep["activeIcon"];
  titleKey: string;
  descriptionKey: string;
}

export interface ReleaseNoteConfig {
  version: string;
  mainTitleKey: string;
  steps: ReleaseNoteStepConfig[];
  createdAt: string;
}

/**
 * Release notes configuration array.
 * IMPORTANT: Keep entries ordered from most recent (first) to oldest (last).
 * The first entry is automatically used as the current version.
 */
export const RELEASE_NOTES: ReleaseNoteConfig[] = ALL_VERSIONS;

/**
 * The current release note configuration (first entry in the array).
 */
export const CURRENT_RELEASE_NOTE: ReleaseNoteConfig | undefined =
  RELEASE_NOTES[0];

/**
 * The current release note version.
 */
export const CURRENT_VERSION: string = CURRENT_RELEASE_NOTE?.version ?? "0.0.0";
