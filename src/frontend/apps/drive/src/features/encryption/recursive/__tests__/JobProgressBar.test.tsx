import { renderToStaticMarkup } from "react-dom/server";
import { JobProgressBar } from "../JobProgressBar";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      `${key}:${options?.done ?? ""}/${options?.count ?? ""}`,
  }),
}));

const render = (props: Parameters<typeof JobProgressBar>[0]) => {
  const html = renderToStaticMarkup(<JobProgressBar {...props} />);
  return {
    text: html.match(/aria-valuetext="([^"]*)"/)?.[1],
    progress: html.match(/--progress:([\d.]+)/)?.[1],
  };
};

describe("JobProgressBar", () => {
  it("is empty before the job starts and says how many items it will process", () => {
    expect(
      render({ phase: "ready", total: 9000, done: 0, mode: "encrypt" }),
    ).toEqual({ text: "encryption.progress.to_encrypt:/9000", progress: "0" });
  });

  it("counts the items processed so far, also once the job stopped on a failure", () => {
    expect(
      render({ phase: "staging", total: 8, done: 2, mode: "decrypt" }),
    ).toEqual({ text: "encryption.progress.decrypted:2/8", progress: "0.25" });
    expect(
      render({ phase: "failed", total: 8, done: 6, mode: "encrypt" }),
    ).toEqual({ text: "encryption.progress.encrypted:6/8", progress: "0.75" });
  });

  it("is full once every item is processed", () => {
    expect(
      render({ phase: "success", total: 8, done: 8, mode: "encrypt" }),
    ).toEqual({ text: "encryption.progress.encrypted:8/8", progress: "1" });
  });
});
