import { fetchAPI } from "@/features/api/fetchApi";
import { StandardDriver } from "../StandardDriver";

jest.mock("@/features/api/fetchApi", () => ({
  fetchAPI: jest.fn().mockResolvedValue({ ok: true, json: async () => ({}) }),
}));

describe("StandardDriver.confirmUserReconciliation", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("calls the confirmation endpoint for the active user", async () => {
    await new StandardDriver().confirmUserReconciliation("active", "abc-123");
    expect(fetchAPI).toHaveBeenCalledWith(
      "user-reconciliations/active/abc-123/",
    );
  });

  it("calls the confirmation endpoint for the inactive user", async () => {
    await new StandardDriver().confirmUserReconciliation("inactive", "def-456");
    expect(fetchAPI).toHaveBeenCalledWith(
      "user-reconciliations/inactive/def-456/",
    );
  });
});
