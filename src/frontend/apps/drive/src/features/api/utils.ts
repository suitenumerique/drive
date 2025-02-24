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

export const baseApiUrl = (apiVersion: string = "1.0") => {
  const origin =
    process.env.NEXT_PUBLIC_API_ORIGIN ||
    (typeof window !== "undefined" ? window.location.origin : "");
  return `${origin}/api/v${apiVersion}/`;
};
