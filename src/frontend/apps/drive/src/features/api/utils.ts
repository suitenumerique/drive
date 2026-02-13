export const errorCauses = async (response: Response, data?: unknown) => {
  const errorsBody = (await response.json()) as Record<
    string,
    string | string[]
  > | null;

  const causes = errorsBody
    ? Object.entries(errorsBody)
        .map(([, value]) => value)
        .flat()
    : undefined;

  return {
    status: response.status,
    cause: causes,
    data,
  };
};

export const getOrigin = () => {
  const configuredOrigin = process.env.NEXT_PUBLIC_API_ORIGIN;
  if (configuredOrigin) {
    return configuredOrigin;
  }

  if (typeof window === "undefined") {
    return "";
  }

  const apiPort = process.env.NEXT_PUBLIC_API_PORT || "8071";
  const current = new URL(window.location.href);
  return `${current.protocol}//${current.hostname}:${apiPort}`;
};
export const baseApiUrl = (apiVersion: string = "1.0") => {
  const origin = getOrigin();
  return `${origin}/api/v${apiVersion}/`;
};

export const isJson = (str: string) => {
  try {
    JSON.parse(str);
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
  } catch (e) {
    return false;
  }
  return true;
};
