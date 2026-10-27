import { Button } from "@gouvfr-lasuite/ui-components";
import { ArrowLeft, ChevronRight } from "@gouvfr-lasuite/ui-components/icons";
import React, { ReactElement, ReactNode } from "react";
import { useTranslation } from "react-i18next";

export type BreadcrumbItem = {
  id: string;
  content: ReactNode;
};

export interface BreadcrumbsProps {
  items: BreadcrumbItem[];
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
    <div className="c__breadcrumbs" data-testid="explorer-breadcrumbs">
      {displayBack && (
        <Button
          icon={<ArrowLeft aria-hidden="true" />}
          color="neutral"
          variant="tertiary"
          className="mr-t"
          onClick={onBack}
          disabled={items.length <= 1}
        >
          {t("Précédent")}
        </Button>
      )}

      {items.map((item, index) => {
        return (
          <React.Fragment key={item.id}>
            {index > 0 && (
              <ChevronRight
                aria-hidden="true"
                className="c__breadcrumbs__separator"
              />
            )}
            {React.cloneElement(item.content as ReactElement<HTMLDivElement>, {
              className: `${
                (
                  (item.content as ReactElement<HTMLDivElement>).props as {
                    className?: string;
                  }
                ).className || ""
              } ${index === items.length - 1 ? "active" : ""}`,
            })}
          </React.Fragment>
        );
      })}
    </div>
  );
};
