import { DEFAULT_CONFIG } from '@/Config'

export type ConfigType = typeof DEFAULT_CONFIG

export enum ClientMessageType {
  ITEMS_SELECTED = 'ITEMS_SELECTED',
}

export interface Item {
  id: string;
  title: string;
  url: string;
  size: number;
  type: "file";
}
