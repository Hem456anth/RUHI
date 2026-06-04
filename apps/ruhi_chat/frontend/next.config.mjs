/** @type {import('next').NextConfig} */
const nextConfig = {
  // RUHI Chat backend host. Override via NEXT_PUBLIC_RUHI_API in .env.local.
  env: {
    NEXT_PUBLIC_RUHI_API: process.env.NEXT_PUBLIC_RUHI_API || "http://localhost:8001",
    NEXT_PUBLIC_RUHI_WS: process.env.NEXT_PUBLIC_RUHI_WS || "ws://localhost:8001",
  },
};

export default nextConfig;
