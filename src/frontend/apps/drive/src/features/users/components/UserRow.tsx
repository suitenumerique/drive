import { User } from "@/features/drivers/types";
import { UserAvatar } from "./UserAvatar";

interface UserProps {
  user: User;
  showEmail?: boolean;
}

export const UserRow = ({ user, showEmail = false }: UserProps) => {
  return (
    <div className="user-row">
      <UserAvatar user={user} />
      <div className="user-row__info">
        <span className="user-row__name">{user.full_name}</span>
        {showEmail && <span className="user-row__email">{user.email}</span>}
      </div>
    </div>
  );
};
