import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  debug: process.env.NODE_ENV === "development",
  reactStrictMode: false,
  webpack: (config) => {
    config.resolve.alias.canvas = false;

    return config;
  },
};

export default nextConfig;
