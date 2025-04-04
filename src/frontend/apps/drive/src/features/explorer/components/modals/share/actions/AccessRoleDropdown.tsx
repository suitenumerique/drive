import { DropdownMenu, DropdownMenuOption } from "@gouvfr-lasuite/ui-kit";
import { useTranslation } from "react-i18next";

type AccessRoleDropdownProps = {
  currentRole: string;
  roles: DropdownMenuOption[];
  onSelect: (role: string) => void;
  canUpdate?: boolean;
  isOpen?: boolean;
  onOpenChange?: (isOpen: boolean) => void;
};

export const AccessRoleDropdown = ({
  roles,
  onSelect,
  canUpdate = true,
  currentRole,
  isOpen,
  onOpenChange,
}: AccessRoleDropdownProps) => {
  const { t } = useTranslation();
  console.log(isOpen);
  if (!canUpdate) {
    return (
      <span className="fs-s clr-greyscale-600">
        {t(`roles.${currentRole}`)}
      </span>
    );
  }
  return (
    <DropdownMenu
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      options={roles}
      selectedValues={[currentRole]}
      onSelectValue={onSelect}
    >
      <div
        role="button"
        className="access-role-dropdown"
        onClick={() => onOpenChange?.(true)}
      >
        <span className="fs-s clr-greyscale-600">
          {t(`roles.${currentRole}`)}
        </span>
        <span className="material-icons">
          {isOpen ? "arrow_drop_up" : "arrow_drop_down"}
        </span>
      </div>
    </DropdownMenu>
  );
};
