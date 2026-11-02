import {
  Filter,
  FilterOption,
  useResponsive,
  CalendarRange,
} from "@gouvfr-lasuite/ui-components";
import { useMemo, useRef } from "react";
import { useTranslation } from "react-i18next";
import { RangeValue } from "react-aria-components";
import { DateValue } from "@internationalized/date";
import { DatePreset, DateRange } from "@/features/explorer/utils/dateFilters";

const MODIFIED_PRESETS: DatePreset[] = [
  "today",
  "last_7_days",
  "last_30_days",
  "this_year",
  "more_than_a_year",
];
const MODIFIED_CUSTOM = "custom";

export type ExplorerFilterModifiedValue = {
  key?: DatePreset;
  customRange?: DateRange;
};

export const ExplorerFilterModified = (props: {
  value?: ExplorerFilterModifiedValue;
  onChange: (value?: ExplorerFilterModifiedValue) => void;
}) => {
  const { t } = useTranslation();
  const { isMobile } = useResponsive();
  const onChangeRef = useRef(props.onChange);
  onChangeRef.current = props.onChange;

  // Holds the range being picked in the calendar. We keep it in a ref so that
  // selecting the end date does not trigger a re-render: updating state here
  // would rebuild the options memo and remount the calendar, detaching its
  // "OK" button mid-interaction (flaky on firefox/webkit). We only commit the
  // range on "OK", when the panel closes anyway.
  const pendingRangeRef = useRef<DateRange>(undefined);

  const options: FilterOption[] = useMemo(() => {
    const presetOptions: FilterOption[] = MODIFIED_PRESETS.map((value) => ({
      label: t(`explorer.filters.modified.options.${value}`),
      value,
      render: () => (
        <div className="explorer__filters__item">
          {t(`explorer.filters.modified.options.${value}`)}
        </div>
      ),
    }));

    // The custom range relies on the calendar popover, which we hide on
    // mobile where there is not enough room to display it comfortably.
    if (isMobile) {
      return presetOptions;
    }

    const customOption: FilterOption = {
      label: props.value?.customRange
        ? `${props.value?.customRange.updated_at_after} - ${props.value?.customRange.updated_at_before}`
        : t("explorer.filters.modified.options.custom"),
      value: MODIFIED_CUSTOM,
      render: () => (
        <div className="explorer__filters__item">
          {props.value?.customRange
            ? `${props.value?.customRange.updated_at_after} - ${props.value?.customRange.updated_at_before}`
            : t("explorer.filters.modified.options.custom")}
        </div>
      ),
      subContent: ({ select, close }) => (
        <CalendarRange
          onChange={(value) => {
            // The calendar props resolve the range value type to `never`
            // because of a duplicated `@internationalized/date` in the
            // dependency tree, so we cast back to the intended shape here.
            const range = value as unknown as RangeValue<DateValue> | null;
            pendingRangeRef.current =
              range?.start && range?.end
                ? {
                    updated_at_after: range.start.toString(),
                    updated_at_before: range.end.toString(),
                  }
                : undefined;
          }}
          onOk={() => {
            select();
            close();
          }}
          onCancel={close}
        />
      ),
    };

    return [...presetOptions, customOption];
  }, [t, props.value?.key, isMobile]);

  return (
    <Filter
      label={t("explorer.filters.modified.label")}
      options={options}
      value={props.value?.key}
      onChange={(key) => {
        if (key) {
          props.onChange({
            key: key as DatePreset,
            customRange:
              key === MODIFIED_CUSTOM ? pendingRangeRef.current : undefined,
          });
        } else {
          props.onChange(undefined);
        }
      }}
    />
  );
};
