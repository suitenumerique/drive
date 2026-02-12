import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@gouvfr-lasuite/cunningham-react";
import { getDriver } from "@/features/config/Config";
import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import type { MountVirtualEntry } from "@/features/drivers/types";

const DEFAULT_LIMIT = 20;

function getParentPath(path: string) {
  if (path === "/") {
    return "/";
  }
  const parts = path.split("/").filter(Boolean);
  parts.pop();
  return `/${parts.join("/")}` || "/";
}

function MountAction(props: {
  label: string;
  capabilityEnabled: boolean;
  abilityEnabled: boolean;
}) {
  const { t } = useTranslation();

  if (!props.capabilityEnabled) {
    return null;
  }

  if (!props.abilityEnabled) {
    return (
      <div>
        <button type="button" disabled>
          {props.label}
        </button>
        <div>{t("explorer.mounts.actions.unavailable")}</div>
      </div>
    );
  }

  return (
    <div>
      <button type="button">{props.label}</button>
    </div>
  );
}

export default function MountBrowsePage() {
  const { t } = useTranslation();
  const router = useRouter();
  const mountId = String(router.query.mount_id ?? "");

  const [path, setPath] = useState("/");
  const [offset, setOffset] = useState(0);

  const {
    data: browse,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["mounts", "browse", mountId, path, DEFAULT_LIMIT, offset],
    enabled: Boolean(mountId),
    refetchOnWindowFocus: false,
    queryFn: () =>
      getDriver().browseMount({
        mountId,
        path,
        limit: DEFAULT_LIMIT,
        offset,
      }),
  });

  const children = browse?.children?.results ?? null;
  const count = browse?.children?.count ?? null;

  const canPrev = useMemo(() => offset > 0, [offset]);
  const canNext = useMemo(() => {
    if (count === null) {
      return false;
    }
    return offset + DEFAULT_LIMIT < count;
  }, [count, offset]);

  const onOpenEntry = (entry: MountVirtualEntry) => {
    if (entry.entry_type !== "folder") {
      return;
    }
    setPath(entry.normalized_path);
    setOffset(0);
  };

  if (isLoading) {
    return <div>{t("explorer.mounts.browse_loading")}</div>;
  }

  if (isError || !browse) {
    return (
      <div>
        <div>{t("explorer.mounts.browse_error")}</div>
        <Button variant="tertiary" onClick={() => refetch()}>
          {t("common.retry")}
        </Button>
      </div>
    );
  }

  const capabilityUpload = Boolean(browse.capabilities?.["mount.upload"]);
  const capabilityPreview = Boolean(browse.capabilities?.["mount.preview"]);
  const capabilityWopi = Boolean(browse.capabilities?.["mount.wopi"]);
  const capabilityShareLink = Boolean(browse.capabilities?.["mount.share_link"]);

  return (
    <div>
      <h1>
        {t("explorer.mounts.title")} — {mountId}
      </h1>

      <div>
        <Link href="/explorer/mounts">{t("explorer.mounts.title")}</Link>
      </div>

      <div>
        {t("explorer.mounts.path")}: <code>{browse.normalized_path}</code>
      </div>

      <div>
        <Button
          variant="tertiary"
          disabled={browse.normalized_path === "/"}
          onClick={() => {
            setPath(getParentPath(browse.normalized_path));
            setOffset(0);
          }}
        >
          {t("common.back")}
        </Button>
      </div>

      <h2>{t("explorer.mounts.actions.title")}</h2>
      {browse.entry.entry_type === "folder" ? (
        <>
          <MountAction
            label={t("explorer.mounts.actions.upload")}
            capabilityEnabled={capabilityUpload}
            abilityEnabled={browse.entry.abilities.upload}
          />
          <MountAction
            label={t("explorer.mounts.actions.share")}
            capabilityEnabled={capabilityShareLink}
            abilityEnabled={browse.entry.abilities.share_link_create}
          />
        </>
      ) : (
        <>
          <MountAction
            label={t("explorer.mounts.actions.preview")}
            capabilityEnabled={capabilityPreview}
            abilityEnabled={browse.entry.abilities.preview}
          />
          <MountAction
            label={t("explorer.mounts.actions.wopi")}
            capabilityEnabled={capabilityWopi}
            abilityEnabled={browse.entry.abilities.wopi}
          />
          <MountAction
            label={t("explorer.mounts.actions.share")}
            capabilityEnabled={capabilityShareLink}
            abilityEnabled={browse.entry.abilities.share_link_create}
          />
        </>
      )}

      <h2>{t("explorer.mounts.children.title")}</h2>
      {children === null ? (
        <div>{t("explorer.mounts.children.none")}</div>
      ) : children.length === 0 ? (
        <div>{t("explorer.mounts.children.empty")}</div>
      ) : (
        <ul>
          {children.map((entry) => (
            <li key={entry.normalized_path}>
              {entry.entry_type === "folder" ? (
                <button type="button" onClick={() => onOpenEntry(entry)}>
                  {entry.name}
                </button>
              ) : (
                <span>{entry.name}</span>
              )}{" "}
              <code>{entry.normalized_path}</code>
            </li>
          ))}
        </ul>
      )}

      {children !== null && (
        <div>
          <Button
            variant="tertiary"
            disabled={!canPrev}
            onClick={() => setOffset(Math.max(0, offset - DEFAULT_LIMIT))}
          >
            {t("common.previous")}
          </Button>
          <Button
            variant="tertiary"
            disabled={!canNext}
            onClick={() => setOffset(offset + DEFAULT_LIMIT)}
          >
            {t("common.next")}
          </Button>
          {count !== null && (
            <span>
              {offset + 1}–{Math.min(offset + DEFAULT_LIMIT, count)} / {count}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

MountBrowsePage.getLayout = getGlobalExplorerLayout;

