import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    noDiscovery: true,
    include: [
      'axios',
      'jwt-decode',
      'leaflet',
      'react',
      'react-dom',
      'react-dom/client',
      'react-dropzone',
      'react-leaflet',
      'react-router-dom',
      'recharts',
    ],
  },
});
