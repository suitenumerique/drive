import { ReleaseNoteConfig } from "../releaseNotes.config";
import { v0_13_0 } from "./v0.13.0";
import { v0_16_0 } from "./v0.16.0";

/**
 * All release notes configurations.
 * IMPORTANT: Keep entries ordered from most recent (first) to oldest (last).
 * The first entry is automatically used as the current version.
 */
export const ALL_VERSIONS: ReleaseNoteConfig[] = [v0_16_0, v0_13_0];
