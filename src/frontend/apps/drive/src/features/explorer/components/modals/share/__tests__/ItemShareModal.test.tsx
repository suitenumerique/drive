import { renderToStaticMarkup } from "react-dom/server";
import { Item, ItemType, LinkReach } from "@/features/drivers/types";
import { ItemShareModal } from "../ItemShareModal";

type ShareModalProps = { linkSettings?: boolean };

let shareModalProps: ShareModalProps | undefined;
let currentItem: Item;

// A declaration, so the hoisted module factories below can reach it.
function mockMutation() {
  return { mutateAsync: jest.fn(), mutate: jest.fn() };
}

jest.mock("@gouvfr-lasuite/ui-components", () => ({
  ...jest.requireActual("@gouvfr-lasuite/ui-components"),
  ShareModal: (props: ShareModalProps) => {
    shareModalProps = props;
    return null;
  },
}));
jest.mock("@/features/explorer/hooks/useMutationsAccesses", () => ({
  useMutationBatchShare: mockMutation,
  useMutationCreateAccess: mockMutation,
  useMutationCreateInvitation: mockMutation,
  useMutationDeleteAccess: mockMutation,
  useMutationDeleteInvitation: mockMutation,
  useMutationUpdateAccess: mockMutation,
  useMutationUpdateInvitation: mockMutation,
}));
jest.mock("@/features/explorer/hooks/useMutations", () => ({
  useMutationUpdateLinkConfiguration: mockMutation,
}));
jest.mock("@/features/explorer/hooks/useQueries", () => ({
  useItem: () => ({ data: currentItem, refetch: jest.fn() }),
  useItemAccesses: () => ({ data: [] }),
  useInfiniteItemInvitations: () => ({
    data: undefined,
    hasNextPage: false,
  }),
}));
jest.mock("@/features/users/hooks/useUserQueries", () => ({
  useUsers: () => ({ data: undefined, isLoading: false }),
}));
jest.mock("@/features/config/ConfigProvider", () => ({
  useConfig: () => ({ config: {} }),
}));
jest.mock("@/features/auth/Auth", () => ({
  useAuth: () => ({ user: { id: "u1" } }),
}));
jest.mock("@/features/encryption/VaultClientProvider", () => ({
  useVaultClient: () => ({ client: null }),
}));
jest.mock("@/features/encryption/sharing/PendingEncryptionSection", () => ({
  PendingEncryptionSection: () => null,
}));
jest.mock("@/features/encryption/sharing/wrapKeyForUser", () => ({}));
jest.mock("@/hooks/useCopyToClipboard", () => ({
  useClipboard: () => jest.fn(),
}));
jest.mock("@tanstack/react-query", () => ({
  useQueryClient: () => ({ invalidateQueries: jest.fn() }),
}));
jest.mock("next/router", () => ({ useRouter: () => ({ push: jest.fn() }) }));
jest.mock("posthog-js", () => ({ capture: jest.fn() }));
jest.mock("@/features/api/APIError", () => ({ errorToString: String }));
jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

const makeItem = (isEncrypted: boolean) =>
  ({
    id: "item-1",
    title: "Report.pdf",
    type: ItemType.FILE,
    path: "root.item-1",
    is_encrypted: isEncrypted,
    link_reach: LinkReach.RESTRICTED,
    abilities: {
      accesses_manage: true,
      accesses_view: true,
      link_select_options: { restricted: [] },
    },
  }) as unknown as Item;

const render = (item: Item) => {
  currentItem = item;
  shareModalProps = undefined;
  renderToStaticMarkup(
    <ItemShareModal isOpen onClose={jest.fn()} item={item} />,
  );
  return shareModalProps!;
};

describe("ItemShareModal link settings", () => {
  it("hides the link settings of an encrypted item", () => {
    expect(render(makeItem(true)).linkSettings).toBe(false);
  });

  it("keeps the link settings of a plain item", () => {
    expect(render(makeItem(false)).linkSettings).toBe(true);
  });
});
