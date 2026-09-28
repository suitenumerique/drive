import { uploadFile } from "../StandardDriver";

class FakeXMLHttpRequest {
  static instances: FakeXMLHttpRequest[] = [];
  headers: Record<string, string> = {};
  upload = { addEventListener: jest.fn() };
  open = jest.fn();
  send = jest.fn();
  abort = jest.fn();
  addEventListener = jest.fn();

  constructor() {
    FakeXMLHttpRequest.instances.push(this);
  }

  setRequestHeader(name: string, value: string) {
    this.headers[name] = value;
  }
}

describe("uploadFile", () => {
  const originalXMLHttpRequest = global.XMLHttpRequest;
  const file = new File(["content"], "file.txt", { type: "text/plain" });

  beforeEach(() => {
    FakeXMLHttpRequest.instances = [];
    global.XMLHttpRequest =
      FakeXMLHttpRequest as unknown as typeof XMLHttpRequest;
  });

  afterEach(() => {
    global.XMLHttpRequest = originalXMLHttpRequest;
  });

  it("does not send an ACL header when the ACL is undefined", () => {
    uploadFile("https://example.com/upload", file, undefined, jest.fn());
    expect(FakeXMLHttpRequest.instances[0].headers).not.toHaveProperty(
      "X-amz-acl",
    );
  });

  it("sends the configured ACL header", () => {
    uploadFile(
      "https://example.com/upload",
      file,
      "bucket-owner-full-control",
      jest.fn(),
    );
    expect(FakeXMLHttpRequest.instances[0].headers["X-amz-acl"]).toBe(
      "bucket-owner-full-control",
    );
  });

  it("does not send an ACL header when the ACL is empty", () => {
    uploadFile("https://example.com/upload", file, "", jest.fn());
    expect(FakeXMLHttpRequest.instances[0].headers).not.toHaveProperty(
      "X-amz-acl",
    );
  });
});
