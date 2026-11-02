import type { NextConfig } from 'next';
const config: NextConfig = {
  poweredByHeader: false,
  devIndicators: false,
  async rewrites() {
    const backend = process.env.KHOJ_BACKEND_URL?.replace(/\/$/, '');
    return {
      beforeFiles:
        process.env.NEXT_PUBLIC_USE_MOCK === '0' && backend
          ? [{ source: '/api/:path*', destination: `${backend}/api/:path*` }]
          : [],
      afterFiles: [],
      fallback: [],
    };
  },
};
export default config;
