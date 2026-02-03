import { ReleaseNoteConfig } from "../../releaseNotes.config";
import { Step1Icon, Step2Icon, Step3Icon } from "./icons";

export const v0_11_1: ReleaseNoteConfig = {
  version: "0.11.1",
  mainTitleKey: "release_notes.v0_11_1.main_title",
  createdAt: "2026-02-03",
  steps: [
    {
      icon: <Step1Icon />,
      activeIcon: <Step1Icon />,
      titleKey: "release_notes.v0_11_1.steps.0.title",
      descriptionKey: "release_notes.v0_11_1.steps.0.description",
    },
    {
      icon: <Step2Icon />,
      activeIcon: <Step2Icon />,
      titleKey: "release_notes.v0_11_1.steps.1.title",
      descriptionKey: "release_notes.v0_11_1.steps.1.description",
    },
    {
      icon: <Step3Icon />,
      activeIcon: <Step3Icon />,
      titleKey: "release_notes.v0_11_1.steps.2.title",
      descriptionKey: "release_notes.v0_11_1.steps.2.description",
    },
  ],
};
