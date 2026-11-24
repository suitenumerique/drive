import { renderToStaticMarkup } from "react-dom/server";
import { Feedback, FeedbackFormButton } from "../Feedback";

let config: Record<string, unknown> = {};

jest.mock("@/features/config/ConfigProvider", () => ({
  useConfig: () => ({ config }),
}));
jest.mock("../useMessagesWidget", () => ({
  useMessagesWidget: () => ({ showWidget: jest.fn() }),
}));
jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key, i18n: {} }),
}));

const LEGACY = {
  FRONTEND_FEEDBACK_BUTTON_SHOW: true,
  FRONTEND_FEEDBACK_ITEMS: { form: { url: "https://legacy.test/" } },
};

describe("FeedbackFormButton", () => {
  beforeEach(() => {
    config = {};
  });

  it("renders nothing without FRONTEND_FEEDBACK_FORM_URL", () => {
    expect(renderToStaticMarkup(<FeedbackFormButton />)).toBe("");
  });

  it("links to FRONTEND_FEEDBACK_FORM_URL in a new tab", () => {
    config = { FRONTEND_FEEDBACK_FORM_URL: "https://forms.test/f" };
    const html = renderToStaticMarkup(<FeedbackFormButton />);
    expect(html).toContain('href="https://forms.test/f"');
    expect(html).toContain('target="_blank"');
    expect(html).toContain("feedback.button");
  });

  it("hides the FRONTEND_FEEDBACK_BUTTON_SHOW button once a form URL is set", () => {
    config = LEGACY;
    expect(renderToStaticMarkup(<Feedback />)).toContain("feedback.button");

    config = { ...LEGACY, FRONTEND_FEEDBACK_FORM_URL: "https://forms.test/f" };
    expect(renderToStaticMarkup(<Feedback />)).toBe("");
  });
});
