import { Button } from "@gouvfr-lasuite/cunningham-react";
import { DropdownMenu } from "@gouvfr-lasuite/ui-kit";
import React, {
  ReactNode,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useTranslation } from "react-i18next";

export type BreadcrumbItem = {
  content: ReactNode;
  label?: string;
  onClick?: () => void;
  isActive?: boolean;
};

export interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  onBack?: () => void;
  displayBack?: boolean;
}

type Cell =
  | { kind: "item"; item: BreadcrumbItem; index: number }
  | { kind: "ellipsis" };

export const Breadcrumbs = ({
  items,
  onBack,
  displayBack = false,
}: BreadcrumbsProps) => {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const itemRefs = useRef<(HTMLDivElement | null)[]>([]);
  const separatorRef = useRef<HTMLSpanElement | null>(null);
  const ellipsisRef = useRef<HTMLDivElement | null>(null);
  const itemWidthsRef = useRef<number[]>([]);
  const separatorWidthRef = useRef(0);
  const ellipsisWidthRef = useRef(0);

  // null = no collapse needed; otherwise items in [1, firstVisibleMiddle) are
  // hidden behind the ellipsis. Item 0 and the last item are always visible.
  const [firstVisibleMiddle, setFirstVisibleMiddle] = useState<number | null>(
    null,
  );
  const [isEllipsisOpen, setIsEllipsisOpen] = useState(false);

  const lastIndex = items.length - 1;

  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Measure once per items change. All separators are identical chevron
    // icons, so a single reference width is enough.
    itemWidthsRef.current = items.map(
      (_, i) => itemRefs.current[i]?.getBoundingClientRect().width ?? 0,
    );
    separatorWidthRef.current =
      separatorRef.current?.getBoundingClientRect().width ?? 0;
    ellipsisWidthRef.current =
      ellipsisRef.current?.getBoundingClientRect().width ?? 0;

    const compute = (containerWidth: number): number | null => {
      if (items.length <= 2) return null;
      const widths = itemWidthsRef.current;
      const sep = separatorWidthRef.current;
      const ellipsis = ellipsisWidthRef.current;

      const totalWidth =
        widths.reduce((sum, w) => sum + w, 0) + sep * lastIndex;
      if (totalWidth <= containerWidth) return null;

      // Reserve: root + last + ellipsis + the two separators framing the
      // ellipsis chain. Then walk middle items right→left, keeping each one
      // that still fits the budget.
      let budget =
        containerWidth - widths[0] - widths[lastIndex] - ellipsis - sep * 2;
      let firstVisible = lastIndex;
      for (let i = lastIndex - 1; i >= 1; i--) {
        const cost = widths[i] + sep;
        if (cost > budget) break;
        budget -= cost;
        firstVisible = i;
      }
      return firstVisible;
    };

    setFirstVisibleMiddle(compute(container.getBoundingClientRect().width));

    if (typeof ResizeObserver === "undefined") return;
    let frame: number | null = null;
    const observer = new ResizeObserver((entries) => {
      if (frame !== null) cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        frame = null;
        const width = entries[0]?.contentRect.width ?? 0;
        setFirstVisibleMiddle(compute(width));
      });
    });
    observer.observe(container);
    return () => {
      if (frame !== null) cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, [items, lastIndex]);

  const showEllipsis = firstVisibleMiddle !== null && firstVisibleMiddle > 1;

  const visibleCells = useMemo<Cell[]>(() => {
    if (items.length === 0) return [];
    const cells: Cell[] = [{ kind: "item", item: items[0], index: 0 }];
    if (showEllipsis) {
      cells.push({ kind: "ellipsis" });
      for (let i = firstVisibleMiddle!; i < lastIndex; i++) {
        cells.push({ kind: "item", item: items[i], index: i });
      }
    } else {
      for (let i = 1; i < lastIndex; i++) {
        cells.push({ kind: "item", item: items[i], index: i });
      }
    }
    if (lastIndex > 0) {
      cells.push({ kind: "item", item: items[lastIndex], index: lastIndex });
    }
    return cells;
  }, [items, showEllipsis, firstVisibleMiddle, lastIndex]);

  const hiddenItems = useMemo(
    () => (showEllipsis ? items.slice(1, firstVisibleMiddle!) : []),
    [items, showEllipsis, firstVisibleMiddle],
  );

  return (
    <>
      {/* Hidden measurement layer: rendered off-screen so we can read each
          item's natural width once per items change. Sibling of the visible
          container so e2e queries scoped to explorer-breadcrumbs don't see it. */}
      <div className="c__breadcrumbs__measure" aria-hidden inert>
        {items.map((item, index) => (
          <div
            key={`m-${index}`}
            ref={(el) => {
              itemRefs.current[index] = el;
            }}
            className="c__breadcrumbs__item"
          >
            {item.content}
          </div>
        ))}
        <span
          ref={separatorRef}
          className="material-icons c__breadcrumbs__separator"
        >
          chevron_right
        </span>
        <div ref={ellipsisRef} className="c__breadcrumbs__ellipsis">
          …
        </div>
      </div>

      <div
        className="c__breadcrumbs"
        data-testid="explorer-breadcrumbs"
        ref={containerRef}
      >
        {displayBack && (
          <Button
            icon={<span className="material-icons">arrow_back</span>}
            color="neutral"
            variant="tertiary"
            className="mr-t"
            onClick={onBack}
            disabled={items.length <= 1}
          >
            {t("Précédent")}
          </Button>
        )}

        {visibleCells.map((cell, i) => (
          <React.Fragment key={cell.kind === "item" ? cell.index : "ellipsis"}>
            {i > 0 && (
              <span className="material-icons c__breadcrumbs__separator">
                chevron_right
              </span>
            )}
            {cell.kind === "item" ? (
              <div
                className={
                  cell.item.isActive
                    ? "c__breadcrumbs__item active"
                    : "c__breadcrumbs__item"
                }
              >
                {cell.item.content}
              </div>
            ) : (
              <EllipsisDropdown
                items={hiddenItems}
                isOpen={isEllipsisOpen}
                setIsOpen={setIsEllipsisOpen}
                ariaLabel={t("explorer.breadcrumbs.show_hidden_folders")}
              />
            )}
          </React.Fragment>
        ))}
      </div>
    </>
  );
};

type EllipsisDropdownProps = {
  items: BreadcrumbItem[];
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  ariaLabel: string;
};

const EllipsisDropdown = ({
  items,
  isOpen,
  setIsOpen,
  ariaLabel,
}: EllipsisDropdownProps) => {
  const options = items.map((item, idx) => ({
    label: item.label ?? "",
    value: String(idx),
    callback: () => {
      item.onClick?.();
      setIsOpen(false);
    },
  }));

  return (
    <DropdownMenu options={options} isOpen={isOpen} onOpenChange={setIsOpen}>
      <button
        type="button"
        className="c__breadcrumbs__ellipsis"
        data-testid="breadcrumb-ellipsis"
        aria-label={ariaLabel}
        onClick={() => setIsOpen(true)}
      >
        …
      </button>
    </DropdownMenu>
  );
};
