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
};

export default nextConfig;
