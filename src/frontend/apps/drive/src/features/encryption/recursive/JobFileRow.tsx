import { Icon } from "@gouvfr-lasuite/ui-kit";
import { useTranslation } from "react-i18next";
import { FileJobRow as FileJobRowType } from "./types";

export const JobFileRow = ({ row }: { row: FileJobRowType }) => {
  const { t } = useTranslation();

  const stateIcon = (() => {
    switch (row.state) {
      case "pending":
        return (
          <Icon
            aria-hidden
            name="schedule"
            color="var(--c--contextuals--content--semantic--neutral--tertiary)"
          />
        );
      case "running":
        return (
          <Icon
            aria-hidden
            name="sync"
            className="drive__encryption-spin"
            color="var(--c--contextuals--content--semantic--brand--primary)"
          />
        );
      case "staged":
        return (
          <Icon
            aria-hidden
            name="cloud_done"
            color="var(--c--contextuals--content--semantic--brand--primary)"
          />
        );
      case "done":
        return (
          <Icon
            aria-hidden
            name="check_circle"
            color="var(--c--contextuals--content--semantic--success--primary)"
          />
        );
      case "skipped":
        return (
          <Icon
            aria-hidden
            name="remove_circle_outline"
            color="var(--c--contextuals--content--semantic--neutral--tertiary)"
          />
        );
      case "failed":
        return (
          <Icon
            aria-hidden
            name="error"
            color="var(--c--contextuals--content--semantic--error--primary)"
          />
        );
    }
  })();

  const caption = (() => {
    if (row.state === "failed" && row.error) return row.error;
    if (row.state === "skipped" && row.skipReason === "already_encrypted") {
      return t("encryption.row.already_encrypted", "Already encrypted");
    }
    if (row.state === "skipped" && row.skipReason === "not_encrypted") {
      return t("encryption.row.not_encrypted", "Not encrypted");
    }
    return row.path || null;
  })();

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.75rem",
        padding: "0.5rem 0.25rem",
        borderBottom:
          "1px solid var(--c--contextuals--border--surface--primary)",
      }}
    >
      <div style={{ flexShrink: 0 }}>{stateIcon}</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            fontWeight: 500,
          }}
        >
          {row.title}
        </div>
        {caption && (
          <div
            style={{
              fontSize: "0.8rem",
              color:
                row.state === "failed"
                  ? "var(--c--contextuals--content--semantic--error--primary)"
                  : "var(--c--contextuals--content--semantic--neutral--tertiary)",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
            title={caption}
          >
            {caption}
          </div>
        )}
      </div>
    </div>
  );
};
