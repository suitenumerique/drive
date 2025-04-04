import { User } from "@/features/drivers/types";

interface UserAvatarProps {
  user: User;
}

export const UserAvatar = ({ user }: UserAvatarProps) => {
  const initials = user.full_name
    .split(" ")
    .map((name) => name[0])
    .join("")
    .toUpperCase();
  return <div className="user-avatar">{initials}</div>;
};
