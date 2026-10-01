import { fetchAPI } from "@/features/api/fetchApi";
import { StandardDriver } from "../StandardDriver";

jest.mock("@/features/api/fetchApi", () => ({
  fetchAPI: jest.fn().mockResolvedValue({ ok: true, json: async () => ({}) }),
}));

describe("StandardDriver.leaveItem", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("calls the leave endpoint for the given item", async () => {
    await new StandardDriver().leaveItem("abc-123");
    expect(fetchAPI).toHaveBeenCalledWith("items/abc-123/leave/", {
      method: "POST",
    });
  });
});
