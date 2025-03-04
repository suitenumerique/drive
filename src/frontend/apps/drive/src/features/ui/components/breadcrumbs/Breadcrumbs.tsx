import { Button } from "@openfun/cunningham-react";
import React, { ReactNode } from "react";
import { useTranslation } from "react-i18next";

export interface BreadcrumbsProps {
  items: { content: ReactNode }[];
  onBack?: () => void;
  displayBack?: boolean;
}

export const Breadcrumbs = ({
  items,
  onBack,
  displayBack = false,
}: BreadcrumbsProps) => {
  const { t } = useTranslation();
  return (
    <div className="c__breadcrumbs">
      {displayBack && (
        <Button
          icon={<span className="material-icons">arrow_back</span>}
          color="tertiary"
          className="mr-t"
          onClick={onBack}
          disabled={items.length <= 1}
        >
          {t("Précédent")}
        </Button>
      )}

      {items.map((item, index) => {
        return (
          <React.Fragment key={index}>
            {index > 0 && (
              <span className="material-icons clr-greyscale-600">
                chevron_right
              </span>
            )}
            {React.cloneElement(item.content as React.ReactElement, {
              className: `${
                (item.content as React.ReactElement).props.className
              } ${index === items.length - 1 ? "active" : ""}`,
            })}
          </React.Fragment>
        );
      })}
    </div>
  );
};
