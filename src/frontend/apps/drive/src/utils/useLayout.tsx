import { useRouter } from "next/router";

export const useIsMinimalLayout = () => {
  const router = useRouter();
  return router.query.minimal === "true";
};
