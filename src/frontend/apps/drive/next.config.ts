import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  debug: process.env.NODE_ENV === "development",
  reactStrictMode: false,
  swcMinify: false,
  // pdfjs-dist v5 standard build uses ES2023 static initialization blocks
  // (`static { ... }`) which Safari < 17.4 doesn't support.
  // The legacy build is pre-transpiled but contains its own webpack runtime
  // that clashes with Next.js bundling. Instead we let SWC transpile the
  // clean ESM standard build so it works on all browsers.
  transpilePackages: ["pdfjs-dist"],
  // Static exports ignore headers: production sets this one in nginx
  // (conf/default.conf). In development, it lets mail clients such as
  // Mailcatcher load the fonts used by emails.
  ...(process.env.NODE_ENV === "development" && {
    async headers() {
      return [
        {
          source: "/assets/fonts/:path*",
          headers: [{ key: "Access-Control-Allow-Origin", value: "*" }],
        },
      ];
    },
  }),
};

export default nextConfig;
