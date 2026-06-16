import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: false, // StrictMode double-mounts in dev, breaks WebSocket
  output: "export", // static files → S3 + CloudFront (rewrites/headers not supported)
  trailingSlash: true, // generates auth/callback/index.html instead of auth/callback.html
};

export default nextConfig;
