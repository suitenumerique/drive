import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  debug: process.env.NODE_ENV === "development",
  reactStrictMode: false,
};

export default nextConfig;
