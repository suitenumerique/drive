import { fetchAPI } from "../api/fetchApi";

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
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any;
}

export class SDKRelayManager {
  static async registerEvent(token: string, event: SDKRelayEvent) {
    return await fetchAPI(`sdk-relay/events/`, {
      method: "POST",
      body: JSON.stringify({
        token,
        event,
      }),
    });
  }
}
