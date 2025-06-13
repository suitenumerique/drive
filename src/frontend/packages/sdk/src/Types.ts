import { DEFAULT_CONFIG } from "@/Config";

export type ConfigType = typeof DEFAULT_CONFIG;

export enum ClientMessageType {
  // Picker.
  ITEMS_SELECTED = "ITEMS_SELECTED",
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
  title: string;
  url: string;
  size: number;
  type: "file";
}
