export const MOUNT_CAPABILITY_KEYS = [
  "mount.upload",
  "mount.preview",
  "mount.wopi",
  "mount.share_link",
] as const;

export type MountCapabilityKey = (typeof MOUNT_CAPABILITY_KEYS)[number];

