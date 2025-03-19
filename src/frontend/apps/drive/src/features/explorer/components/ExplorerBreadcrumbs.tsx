import { Breadcrumbs } from "@/features/ui/components/breadcrumbs/Breadcrumbs";
import { Button } from "@openfun/cunningham-react";
import workspaceLogo from "@/assets/workspace_logo.svg";
import { NavigationEventType, useExplorer } from "./ExplorerContext";
import { useMemo } from "react";
import { getAncestors } from "../utils/tree";

export const ExplorerBreadcrumbs = () => {
  const { tree, item, onNavigate, treeObject } = useExplorer();

  const getBreadcrumbsItems = () => {
    if (!tree || !item) {
      return [];
    }

    const nodes = treeObject.nodes;

    // const ancestors = [];
    const ancestors = nodes.length > 0 ? getAncestors(nodes[1], item) : [];
    return ancestors.map((ancestor, index) => {
      return {
        content: (
          <button
            onClick={(e) => {
              e.preventDefault();
              onNavigate({
                type: NavigationEventType.ITEM,
                item: ancestor,
              });
            }}
            className="c__breadcrumbs__button"
          >
            {index === 0 && <img src={workspaceLogo.src} alt="Lasuite" />}
            {ancestor.title}
          </button>
        ),
      };
    });
  };

  const breadcrumbsItems = useMemo(() => getBreadcrumbsItems(), [tree, item]);

  return (
    <div className="explorer__content__breadcrumbs">
      <Breadcrumbs items={breadcrumbsItems} />
      <div className="explorer__content__breadcrumbs__actions">
        <Button
          icon={<span className="material-icons">info</span>}
          color="primary-text"
        ></Button>
      </div>
    </div>
  );
};
