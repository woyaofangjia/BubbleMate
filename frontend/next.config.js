/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // 允许访问本地API
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ];
  },
};

module.exports = nextConfig;