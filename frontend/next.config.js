/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Playwright runs its own dev server with NEXT_DIST_DIR=.next-e2e so it
  // never clashes with a `npm run dev` you already have open.
  distDir: process.env.NEXT_DIST_DIR || ".next",
};

module.exports = nextConfig;