import type { Key } from "@react-types/shared";
import {
  cloneElement,
  type MouseEvent,
  type ReactElement,
  type SyntheticEvent,
  useMemo,
  useRef,
  useState,
} from "react";
import clsx from "clsx";
import {
  DismissButton,
  FocusScope,
  OverlayContainer,
  useMenu,
  useMenuItem,
  useOverlay,
} from "react-aria";
import {
  Item as CollectionItem,
  type Node,
  type TreeState,
  useMenuTriggerState,
  useTreeState,
} from "react-stately";

export type ContextMenuOption = {
  id: Key;
  label: string;
  onSelect?: () => void;
  disabled?: boolean;
};

type ContextMenuProps = {
  items: ContextMenuOption[];
  children: ReactElement<{ onContextMenu?: (event: MouseEvent) => void }>;
  ariaLabel?: string;
  shouldOpen?: (event: MouseEvent) => boolean;
  onOpen?: (event: MouseEvent) => void;
};

const MENU_SAFE_MARGIN = 12;

export const ContextMenu = ({
  items,
  children,
  ariaLabel = "Menu contextuel",
  shouldOpen,
  onOpen,
}: ContextMenuProps) => {
  const state = useMenuTriggerState({});
  const [position, setPosition] = useState({ x: 0, y: 0 });

  const handleContextMenu = (event: MouseEvent) => {
    if (event.defaultPrevented) {
      return;
    }

    if (shouldOpen && !shouldOpen(event)) {
      return;
    }

    event.preventDefault();
    onOpen?.(event);

    const viewportWidth =
      window.innerWidth || document.documentElement.clientWidth || 0;
    const viewportHeight =
      window.innerHeight || document.documentElement.clientHeight || 0;

    const estimatedWidth = 240;
    const estimatedHeight = Math.min(items.length * 44, 300);

    const safeX = Math.max(
      MENU_SAFE_MARGIN,
      Math.min(event.clientX, viewportWidth - estimatedWidth - MENU_SAFE_MARGIN)
    );
    const safeY = Math.max(
      MENU_SAFE_MARGIN,
      Math.min(
        event.clientY,
        viewportHeight - estimatedHeight - MENU_SAFE_MARGIN
      )
    );

    setPosition({ x: safeX, y: safeY });
    state.open();
  };

  const trigger = cloneElement(children, {
    onContextMenu: composeEventHandlers(
      children.props.onContextMenu,
      handleContextMenu
    ),
  });

  if (!items.length) {
    return children;
  }

  return (
    <>
      {trigger}
      {state.isOpen && (
        <ContextMenuOverlay
          items={items}
          ariaLabel={ariaLabel}
          position={position}
          onClose={state.close}
        />
      )}
    </>
  );
};

const ContextMenuOverlay = ({
  items,
  ariaLabel,
  position,
  onClose,
}: {
  items: ContextMenuOption[];
  ariaLabel: string;
  position: { x: number; y: number };
  onClose: () => void;
}) => {
  const overlayRef = useRef<HTMLDivElement>(null);
  const { overlayProps } = useOverlay(
    {
      isOpen: true,
      isDismissable: true,
      shouldCloseOnBlur: true,
      onClose,
    },
    overlayRef
  );

  return (
    <OverlayContainer>
      <FocusScope restoreFocus>
        <div
          {...overlayProps}
          ref={overlayRef}
          className="context-menu"
          style={{ top: position.y, left: position.x }}
        >
          <DismissButton onDismiss={onClose} />
          <ContextMenuList
            ariaLabel={ariaLabel}
            items={items}
            onClose={onClose}
          />
          <DismissButton onDismiss={onClose} />
        </div>
      </FocusScope>
    </OverlayContainer>
  );
};

const ContextMenuList = ({
  ariaLabel,
  items,
  onClose,
}: {
  ariaLabel: string;
  items: ContextMenuOption[];
  onClose: () => void;
}) => {
  const listRef = useRef<HTMLUListElement>(null);
  const disabledKeys = useMemo<Set<Key>>(() => {
    const ids = items.filter((item) => item.disabled).map((item) => item.id);
    return new Set(ids);
  }, [items]);

  const state = useTreeState<ContextMenuOption>({
    selectionMode: "none",
    disabledKeys,
    items,
    children: (item) => (
      <CollectionItem key={item.id} textValue={item.label}>
        {item.label}
      </CollectionItem>
    ),
  });

  const { menuProps } = useMenu(
    {
      "aria-label": ariaLabel,
      onAction: (key: Key) => {
        const selected = items.find((item) => item.id === key);
        selected?.onSelect?.();
        onClose();
      },
    },
    state,
    listRef
  );

  return (
    <ul {...menuProps} ref={listRef} className="context-menu__list">
      {[...state.collection].map((item) => (
        <ContextMenuListItem key={item.key} item={item} state={state} />
      ))}
    </ul>
  );
};

type ContextMenuListItemProps = {
  item: Node<ContextMenuOption>;
  state: TreeState<ContextMenuOption>;
};

const ContextMenuListItem = ({ item, state }: ContextMenuListItemProps) => {
  const ref = useRef<HTMLLIElement>(null);
  const { menuItemProps, isFocused, isDisabled } = useMenuItem(
    {
      key: item.key,
      closeOnSelect: true,
    },
    state,
    ref
  );

  return (
    <li
      {...menuItemProps}
      ref={ref}
      className={clsx("context-menu__item", {
        "context-menu__item--focused": isFocused,
        "context-menu__item--disabled": isDisabled,
      })}
    >
      {item.rendered}
    </li>
  );
};

const composeEventHandlers =
  <
    EventType extends SyntheticEvent<unknown>,
    Handler extends ((event: EventType) => void) | undefined,
  >(
    userHandler: Handler,
    oursHandler?: (event: EventType) => void
  ) =>
  (event: EventType) => {
    userHandler?.(event);
    if (event.defaultPrevented) {
      return;
    }
    oursHandler?.(event);
  };
