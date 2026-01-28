import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  debug: process.env.NODE_ENV === "development",
  reactStrictMode: false,
  swcMinify: false,
  experimental: {
    esmExternals: 'loose'
  }
};

export default nextConfig;
