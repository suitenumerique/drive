import { Breadcrumbs } from "@/features/ui/components/breadcrumbs/Breadcrumbs";
import { Button } from "@openfun/cunningham-react";
import Link from "next/link";
import workspaceLogo from "@/assets/workspace_logo.svg";

export const ExplorerBreadcrumbs = () => {
  return (
    <div className="explorer__content__breadcrumbs">
      <Breadcrumbs
        items={[
          {
            content: (
              <Link href="/explorer" className="c__breadcrumbs__button">
                <img src={workspaceLogo.src} alt="Lasuite" />
                Mon Espace
              </Link>
            ),
          },
          {
            content: (
              <Link href="/explorer" className="c__breadcrumbs__button">
                Documents
              </Link>
            ),
          },
          {
            content: (
              <Link href="/explorer" className="c__breadcrumbs__button">
                Projet 2024
              </Link>
            ),
          },
          {
            content: (
              <Link href="/explorer" className="c__breadcrumbs__button">
                Resources juridiques
              </Link>
            ),
          },
          {
            content: (
              <Link href="/explorer" className="c__breadcrumbs__button">
                Réglementation
              </Link>
            ),
          },
        ]}
      />
      <div className="explorer__content__breadcrumbs__actions">
        <Button
          icon={<span className="material-icons">info</span>}
          color="primary-text"
        ></Button>
      </div>
    </div>
  );
};
