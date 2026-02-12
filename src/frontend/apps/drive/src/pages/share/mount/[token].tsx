import { fetchAPI } from "@/features/api/fetchApi";
import { APIError } from "@/features/api/APIError";
import { useRouter } from "next/router";
import { useEffect, useMemo, useState } from "react";

type PublicMountShareEntry = {
  normalized_path: string;
  entry_type: "file" | "folder";
  name: string;
  size?: number | null;
  modified_at?: string | null;
};

type BrowseResponse = {
  normalized_path: string;
  entry: PublicMountShareEntry;
  children:
    | null
    | {
        count: number;
        next: string | null;
        previous: string | null;
        results: PublicMountShareEntry[];
      };
};

const SHARE_OPEN_TIMEOUT_MS = 15000;

export default function MountShareLinkPage() {
  const router = useRouter();

  const token = useMemo(() => {
    const raw = router.query.token;
    return typeof raw === "string" ? raw : null;
  }, [router.query.token]);

  const path = useMemo(() => {
    const raw = router.query.path;
    return typeof raw === "string" ? raw : null;
  }, [router.query.path]);

  const [data, setData] = useState<BrowseResponse | null>(null);
  const [error, setError] = useState<
    "not_found" | "gone" | "timeout" | "unknown" | null
  >(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) {
      return;
    }

    setLoading(true);
    setError(null);

    fetchAPI(
      `mount-share-links/${token}/browse/`,
      path ? { params: { path } } : undefined,
      { redirectOn40x: false, timeoutMs: SHARE_OPEN_TIMEOUT_MS },
    )
      .then((r) => r.json())
      .then((payload) => setData(payload))
      .catch((e) => {
        if (e instanceof APIError && e.status === 404) {
          setError("not_found");
          return;
        }
        if (e instanceof APIError && e.status === 410) {
          setError("gone");
          return;
        }
        if (e instanceof Error && e.message.toLowerCase().includes("timeout")) {
          setError("timeout");
          return;
        }
        setError("unknown");
      })
      .finally(() => setLoading(false));
  }, [path, token]);

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
        {error === "gone" ? (
          <p>Link expired or target moved. Ask the sender to create a new link.</p>
        ) : error === "timeout" ? (
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

  const current = data.entry;
  const children = data.children?.results ?? [];

  return (
    <main style={{ padding: 24, maxWidth: 900, margin: "0 auto" }}>
      <header style={{ marginBottom: 16 }}>
        <h1 style={{ marginBottom: 8 }}>{current.name}</h1>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          {data.normalized_path !== "/" && (
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
        </div>
      </header>

      {current.entry_type === "folder" && (
        <section>
          <h2 style={{ marginBottom: 8 }}>Contents</h2>
          {children.length === 0 ? (
            <p>This folder is empty.</p>
          ) : (
            <ul style={{ paddingLeft: 18 }}>
              {children.map((child) => (
                <li
                  key={`${child.entry_type}:${child.normalized_path}`}
                  style={{ marginBottom: 6 }}
                >
                  {child.entry_type === "folder" ? (
                    <button
                      type="button"
                      onClick={() =>
                        router.push(
                          {
                            pathname: router.pathname,
                            query: { token, path: child.normalized_path },
                          },
                          undefined,
                          { shallow: true },
                        )
                      }
                    >
                      {child.name}
                    </button>
                  ) : (
                    <span>{child.name}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {current.entry_type === "file" && (
        <section>
          <p>This file is shared, but download is not available yet.</p>
        </section>
      )}
    </main>
  );
}

