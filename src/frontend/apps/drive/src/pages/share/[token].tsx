import { fetchAPI } from "@/features/api/fetchApi";
import { ItemType } from "@/features/drivers/types";
import { APIError } from "@/features/api/APIError";
import { useRouter } from "next/router";
import { useEffect, useMemo, useState } from "react";

type PublicShareItem = {
  id: string;
  title: string;
  type: ItemType;
  filename: string | null;
  mimetype: string | null;
  size: number | null;
  created_at: string;
  updated_at: string;
  upload_state: string | null;
  url: string | null;
  url_preview: string | null;
};

type BrowseResponse = {
  root_item_id: string;
  item: PublicShareItem;
  children:
    | null
    | {
        count: number;
        next: string | null;
        previous: string | null;
        results: PublicShareItem[];
      };
};

const SHARE_OPEN_TIMEOUT_MS = 15000;

export default function ShareLinkPage() {
  const router = useRouter();
  const token = useMemo(() => {
    const raw = router.query.token;
    return typeof raw === "string" ? raw : null;
  }, [router.query.token]);

  const itemId = useMemo(() => {
    const raw = router.query.item_id;
    return typeof raw === "string" ? raw : null;
  }, [router.query.item_id]);

  const [data, setData] = useState<BrowseResponse | null>(null);
  const [error, setError] = useState<"not_found" | "timeout" | "unknown" | null>(
    null,
  );
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) {
      return;
    }

    setLoading(true);
    setError(null);

    fetchAPI(
      `share-links/${token}/browse/`,
      itemId ? { params: { item_id: itemId } } : undefined,
      { redirectOn40x: false, timeoutMs: SHARE_OPEN_TIMEOUT_MS },
    )
      .then((r) => r.json())
      .then((payload) => {
        setData(payload);
      })
      .catch((e) => {
        if (e instanceof APIError && e.status === 404) {
          setError("not_found");
          return;
        }
        if (e instanceof Error && e.message.toLowerCase().includes("timeout")) {
          setError("timeout");
          return;
        }
        setError("unknown");
      })
      .finally(() => setLoading(false));
  }, [itemId, token]);

  if (!token) {
    return null;
  }

  if (loading) {
    return (
      <main style={{ padding: 24 }}>
        <h1>Opening link…</h1>
        <p>Please wait.</p>
      </main>
    );
  }

  if (error) {
    return (
      <main style={{ padding: 24 }}>
        <h1>Link unavailable</h1>
        {error === "timeout" ? (
          <p>This is taking too long. Please retry.</p>
        ) : (
          <p>This link is invalid, expired, or not public.</p>
        )}
      </main>
    );
  }

  if (!data) {
    return null;
  }

  const current = data.item;
  const children = data.children?.results ?? [];

  return (
    <main style={{ padding: 24, maxWidth: 900, margin: "0 auto" }}>
      <header style={{ marginBottom: 16 }}>
        <h1 style={{ marginBottom: 8 }}>{current.title}</h1>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          {itemId && itemId !== data.root_item_id && (
            <button
              type="button"
              onClick={() =>
                router.push(
                  { pathname: router.pathname, query: { token } },
                  undefined,
                  { shallow: true },
                )
              }
            >
              Back to root
            </button>
          )}
          {current.type === ItemType.FILE && current.url && (
            <a href={current.url} target="_blank" rel="noreferrer">
              Download
            </a>
          )}
        </div>
      </header>

      {current.type === ItemType.FOLDER && (
        <section>
          <h2 style={{ marginBottom: 8 }}>Contents</h2>
          {children.length === 0 ? (
            <p>This folder is empty.</p>
          ) : (
            <ul style={{ paddingLeft: 18 }}>
              {children.map((child) => (
                <li key={child.id} style={{ marginBottom: 6 }}>
                  {child.type === ItemType.FOLDER ? (
                    <button
                      type="button"
                      onClick={() =>
                        router.push(
                          {
                            pathname: router.pathname,
                            query: { token, item_id: child.id },
                          },
                          undefined,
                          { shallow: true },
                        )
                      }
                    >
                      {child.title}
                    </button>
                  ) : child.url ? (
                    <a href={child.url} target="_blank" rel="noreferrer">
                      {child.title}
                    </a>
                  ) : (
                    <span>{child.title}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </main>
  );
}
