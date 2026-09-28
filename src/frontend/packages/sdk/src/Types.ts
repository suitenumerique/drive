import { DEFAULT_CONFIG } from "@/Config";

export type ConfigType = typeof DEFAULT_CONFIG;

export enum ClientMessageType {
  // Picker.
  ITEMS_SELECTED = "ITEMS_SELECTED",
  CANCEL = "CANCEL",
  // Saver
  SAVER_READY = "SAVER_READY",
  SAVER_PAYLOAD = "SAVER_PAYLOAD",
  ITEM_SAVED = "ITEM_SAVED",
}

export interface SDKRelayEvent {
  type: string;
  data: any;
}

export interface Item {
  id: string;
  size: number;
  title: string;
  type: "file";
  url_permalink: string;
  url_preview: string;
  url: string;
}
