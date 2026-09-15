import { fetchAPI } from "@/features/api/fetchApi";
import { Role } from "@/features/drivers/types";
import { StandardDriver } from "../StandardDriver";

jest.mock("@/features/api/fetchApi", () => ({
  fetchAPI: jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ results: [] }),
  }),
}));

describe("StandardDriver.getItemAskForAccesses", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("calls the list endpoint and returns results", async () => {
    const requests = [{ id: "req-1" }, { id: "req-2" }];
    (fetchAPI as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ results: requests }),
    });

    const result = await new StandardDriver().getItemAskForAccesses("item-123");

    expect(fetchAPI).toHaveBeenCalledWith("items/item-123/ask-for-access/");
    expect(result).toEqual(requests);
  });
});

describe("StandardDriver.createAskForAccess", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("calls the create endpoint with an empty body when no role is given", async () => {
    await new StandardDriver().createAskForAccess({ itemId: "item-123" });

    expect(fetchAPI).toHaveBeenCalledWith("items/item-123/ask-for-access/", {
      method: "POST",
      body: JSON.stringify({}),
    });
  });

  it("calls the create endpoint with the role in the body when a role is given", async () => {
    await new StandardDriver().createAskForAccess({
      itemId: "item-123",
      role: Role.READER,
    });

    expect(fetchAPI).toHaveBeenCalledWith("items/item-123/ask-for-access/", {
      method: "POST",
      body: JSON.stringify({ role: Role.READER }),
    });
  });
});

describe("StandardDriver.deleteAskForAccess", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("calls the delete endpoint for the given request", async () => {
    await new StandardDriver().deleteAskForAccess({
      itemId: "item-123",
      askForAccessId: "req-456",
    });

    expect(fetchAPI).toHaveBeenCalledWith(
      "items/item-123/ask-for-access/req-456/",
      { method: "DELETE" },
    );
  });
});

describe("StandardDriver.acceptAskForAccess", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("calls the accept endpoint with an empty body when no role override is given", async () => {
    await new StandardDriver().acceptAskForAccess({
      itemId: "item-123",
      askForAccessId: "req-456",
    });

    expect(fetchAPI).toHaveBeenCalledWith(
      "items/item-123/ask-for-access/req-456/accept/",
      { method: "POST", body: JSON.stringify({}) },
    );
  });

  it("calls the accept endpoint with the role override in the body when a role is given", async () => {
    await new StandardDriver().acceptAskForAccess({
      itemId: "item-123",
      askForAccessId: "req-456",
      role: Role.EDITOR,
    });

    expect(fetchAPI).toHaveBeenCalledWith(
      "items/item-123/ask-for-access/req-456/accept/",
      { method: "POST", body: JSON.stringify({ role: Role.EDITOR }) },
    );
  });
});
