import { useTranslation } from "react-i18next";
import { getDriver } from "../config/Config";
import { useState } from "react";
import { Item, LinkReach, LinkRole } from "../drivers/types";
import { Button } from "@openfun/cunningham-react";
import { Spinner } from "@gouvfr-lasuite/ui-kit";
import { ClientMessageType, SDKRelayManager } from "./SdkRelayManager";

export const PickerFooter = ({
  token,
  selectedItems,
}: {
  token: string;
  selectedItems: Item[];
}) => {
  const { t } = useTranslation();

  const driver = getDriver();

  const [waitForClosing, setWaitForClosing] = useState(false);

  const onChoose = async () => {
    const promises = selectedItems.map((item) => {
      return driver.updateItem({
        id: item.id,
        link_reach: LinkReach.PUBLIC,
        link_role: LinkRole.READER,
      });
    });

    await Promise.all(promises);

    const response = await SDKRelayManager.registerEvent(token, {
      type: ClientMessageType.ITEMS_SELECTED,
      data: {
        items: selectedItems,
      },
    });
    console.log("response", response);
    setWaitForClosing(true);
  };

  const onCancel = () => {
    window.close();
  };

  return (
    <div className="sdk__explorer__footer">
      <div className="sdk__explorer__footer__caption">
        {t("sdk.explorer.picker_label", {
          count: selectedItems.length,
        })}
      </div>
      <div className="sdk__explorer__footer__actions">
        <Button
          color="primary-text"
          onClick={onCancel}
          disabled={waitForClosing}
        >
          {t("sdk.explorer.cancel")}
        </Button>
        <Button
          onClick={onChoose}
          disabled={waitForClosing || selectedItems.length === 0}
          icon={waitForClosing ? <Spinner size="sm" /> : undefined}
        >
          {t("sdk.explorer.choose")}
        </Button>
      </div>
    </div>
  );
};
