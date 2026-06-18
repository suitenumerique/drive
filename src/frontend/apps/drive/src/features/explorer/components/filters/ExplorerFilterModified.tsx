import { Filter, FilterOption } from "@gouvfr-lasuite/ui-kit";
import { DateRangePicker } from "@gouvfr-lasuite/cunningham-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Key } from "react-aria-components";
import {
  DatePreset,
  DateRange,
  presetRange,
} from "@/features/explorer/utils/dateFilters";
import { ALL, getResetOption } from "./filterUtils";

const MODIFIED_PRESETS: DatePreset[] = [
  "today",
  "last_7_days",
  "last_30_days",
  "this_year",
  "more_than_a_year",
];
const MODIFIED_CUSTOM = "custom";

export const ExplorerFilterModified = (props: {
  value: DateRange | null;
  onChange: (range: DateRange | null) => void;
}) => {
  const { t } = useTranslation();
  const [preset, setPreset] = useState<Key | null>(null);
  const [isCustom, setIsCustom] = useState(false);

  // Reset the local selection when the range is cleared from outside (e.g. the
  // modal's global reset). Track the transition to empty so picking "custom",
  // which leaves the range empty until dates are chosen, is not cancelled.
  const previousValue = useRef(props.value);
  useEffect(() => {
    const wasSet = previousValue.current;
    previousValue.current = props.value;
    if (wasSet && !props.value) {
      setPreset(null);
      setIsCustom(false);
    }
  }, [props.value]);

  const options: FilterOption[] = useMemo(
    () => [
      { ...getResetOption(t), showSeparator: true },
      ...MODIFIED_PRESETS.map((value) => ({
        label: t(`explorer.filters.modified.options.${value}`),
        value,
        render: () => (
          <div className="explorer__filters__item">
            {t(`explorer.filters.modified.options.${value}`)}
          </div>
        ),
      })),
      {
        label: t("explorer.filters.modified.options.custom"),
        value: MODIFIED_CUSTOM,
        render: () => (
          <div className="explorer__filters__item">
            {t("explorer.filters.modified.options.custom")}
          </div>
        ),
      },
    ],
    [t],
  );

  const onSelectionChange = (key: Key | null) => {
    if (key === ALL) {
      setPreset(null);
      setIsCustom(false);
      props.onChange(null);
      return;
    }
    if (key === MODIFIED_CUSTOM) {
      setPreset(key);
      setIsCustom(true);
      return;
    }
    setPreset(key);
    setIsCustom(false);
    props.onChange(presetRange(key as DatePreset));
  };

  return (
    <>
      <Filter
        label={t("explorer.filters.modified.label")}
        options={options}
        selectedKey={preset}
        onSelectionChange={onSelectionChange}
      />
      {isCustom && (
        <DateRangePicker
          compact
          hideLabel
          startLabel={t("explorer.filters.modified.start")}
          endLabel={t("explorer.filters.modified.end")}
          onChange={(range) =>
            // The picker emits ISO datetimes; the backend wants date-only bounds.
            props.onChange(
              range
                ? {
                    updated_at_after: range[0].slice(0, 10),
                    updated_at_before: range[1].slice(0, 10),
                  }
                : null,
            )
          }
        />
      )}
    </>
  );
};
