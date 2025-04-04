import { Access, Role } from "@/features/drivers/types";
import { UserRow } from "@/features/users/components/UserRow";
import { QuickSearchItemTemplate } from "@gouvfr-lasuite/ui-kit";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { AccessRoleDropdown } from "../actions/AccessRoleDropdown";

type AccessRowItemProps = {
  access: Access;
};

export const AccessRowItem = ({ access }: AccessRowItemProps) => {
  const { t } = useTranslation();
  const [currentRole, setCurrentRole] = useState<Role>(access.role);
  const [isOpen, setIsOpen] = useState(false);
  const rolesOptions = useMemo(
    () =>
      Object.values(Role).map((role) => ({
        label: t(`roles.${role}`),
        value: role,
      })),
    [t]
  );

  return (
    <QuickSearchItemTemplate
      left={
        <div style={{ width: "100%", flex: 1 }}>
          <UserRow user={access.user} showEmail />
        </div>
      }
      right={
        <AccessRoleDropdown
          isOpen={isOpen}
          currentRole={currentRole}
          roles={rolesOptions}
          onSelect={(role) => {
            setCurrentRole(role as Role);
          }}
          onOpenChange={(isOpen) => {
            console.log("onOpenChange", isOpen);
            setIsOpen(isOpen);
          }}
        />
      }
    />
  );
};
