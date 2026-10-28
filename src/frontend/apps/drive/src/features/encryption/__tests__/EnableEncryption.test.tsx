import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MissingEncryptionKeysPanel } from "../MissingEncryptionKeysModal";
import { ModalRecursiveEncrypt } from "../ModalRecursiveEncrypt";
import { Item, ItemType } from "@/features/drivers/types";

type ButtonProps = {
  children?: ReactNode;
  variant?: string;
  href?: string;
  onClick?: () => void;
};

let buttons: ButtonProps[] = [];
const vault = {
  hasKeys: false as boolean | null,
  openEncryptionOnboarding: jest.fn(),
};
const job = {
  phase: "ready",
  rows: [],
  validationErrors: [] as string[],
  topError: null,
  pendingUserCount: 0,
  canConfirm: true,
  confirm: jest.fn(),
  retry: jest.fn(),
  totalProcessable: 0,
  doneCount: 0,
};

jest.mock("@gouvfr-lasuite/ui-components", () => ({
  ...jest.requireActual("@gouvfr-lasuite/ui-components"),
  Button: (props: ButtonProps) => {
    buttons.push(props);
    return <button>{props.children}</button>;
  },
  Icon: () => null,
  Modal: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));
jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: unknown) =>
      typeof fallback === "string" ? fallback : key,
  }),
}));
jest.mock("../VaultClientProvider", () => ({
  useVaultClient: () => vault,
}));
jest.mock("../recursive/useRecursiveEncryptionJob", () => ({
  useRecursiveEncryptionJob: () => job,
}));
jest.mock("../recursive/JobProgressBar", () => ({
  JobProgressBar: () => null,
}));
jest.mock("../recursive/JobFileRow", () => ({ JobFileRow: () => null }));

const render = (node: ReactNode) => {
  buttons = [];
  renderToStaticMarkup(<>{node}</>);
  return buttons;
};

const enableButton = (rendered: ButtonProps[]) =>
  rendered.find((b) => b.children === "Enable encryption");

describe("MissingEncryptionKeysPanel", () => {
  it("offers a primary button that opens the onboarding", () => {
    const onSetUp = jest.fn();
    const button = enableButton(
      render(<MissingEncryptionKeysPanel onSetUp={onSetUp} />),
    );
    expect(button).toBeDefined();
    // The design system's primary variant is its default one.
    expect([undefined, "primary"]).toContain(button!.variant);
    button!.onClick!();
    expect(onSetUp).toHaveBeenCalled();
  });

  it("only leads home without an onboarding to open", () => {
    expect(
      render(<MissingEncryptionKeysPanel />).map((button) => button.href),
    ).toEqual(["/"]);
  });
});

describe("ModalRecursiveEncrypt", () => {
  const item = { id: "i1", title: "Doc", type: ItemType.FILE } as Item;

  beforeEach(() => {
    vault.openEncryptionOnboarding.mockClear();
  });

  it("asks to enable encryption instead of encrypting without keys", () => {
    vault.hasKeys = false;
    const onClose = jest.fn();
    const rendered = render(
      <ModalRecursiveEncrypt isOpen onClose={onClose} item={item} />,
    );
    expect(rendered.find((b) => b.children === "Encrypt")).toBeUndefined();
    const button = enableButton(rendered);
    expect(button).toBeDefined();
    button!.onClick!();
    expect(onClose).toHaveBeenCalled();
    expect(vault.openEncryptionOnboarding).toHaveBeenCalled();
  });

  it("offers to encrypt once keys are on this device", () => {
    vault.hasKeys = true;
    const rendered = render(
      <ModalRecursiveEncrypt isOpen onClose={jest.fn()} item={item} />,
    );
    expect(rendered.find((b) => b.children === "Encrypt")).toBeDefined();
    expect(enableButton(rendered)).toBeUndefined();
  });
});
