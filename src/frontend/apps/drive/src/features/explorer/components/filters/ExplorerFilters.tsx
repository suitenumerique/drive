import { useAppExplorer } from "@/features/explorer/components/app-view/AppExplorer";
import { useAuth } from "@/features/auth/Auth";
import { ALL, handleFilterChange } from "./filterUtils";
import { ExplorerFilterCategory } from "./ExplorerFilterCategory";
import { ExplorerFilterContact } from "./ExplorerFilterContact";
import { ExplorerFilterModified } from "./ExplorerFilterModified";
import { SmartScroller } from "@gouvfr-lasuite/ui-components";

export const ExplorerFilters = () => {
  const { filters, onFiltersChange } = useAppExplorer();
  const { user } = useAuth();

  const onChange = (name: string, value: unknown) => {
    onFiltersChange?.(handleFilterChange(filters, name, value));
  };

  return (
    <div className="explorer__filters__container">
      <SmartScroller>
        <div className="explorer__filters">
          <ExplorerFilterCategory
            value={filters?.category ?? null}
            onChange={(value) => onChange("category", value)}
          />
          {/* Contacts and user search both require authentication. */}
          {user && (
            <ExplorerFilterContact
              value={filters?.contact}
              onChange={(value) => onChange("contact", value ?? ALL)}
            />
          )}
          <ExplorerFilterModified
            value={filters?.modified}
            onChange={(value) => onChange("modified", value ?? null)}
          />
        </div>
      </SmartScroller>
    </div>
  );
};
