import { UserTokenManager } from '@/features/user-tokens';
import {GlobalLayout} from "@/features/layouts/components/global/GlobalLayout";
import {DefaultLayout} from "@/features/layouts/components/default/DefaultLayout";

export default function UserTokensPage() {
  return <UserTokenManager />;
}

UserTokensPage.getLayout = function getLayout(page: React.ReactElement) {
  return (
    <GlobalLayout>
      <DefaultLayout>{page}</DefaultLayout>
    </GlobalLayout>
  );
};
