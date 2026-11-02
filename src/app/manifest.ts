import type { MetadataRoute } from 'next';
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'KHOJ — Every search matters',
    short_name: 'KHOJ',
    description: 'Find and report missing persons in India. Frontend demo.',
    start_url: '/',
    display: 'standalone',
    background_color: '#f1f2ec',
    theme_color: '#f1f2ec',
    icons: [
      { src: '/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
      { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
  };
}
