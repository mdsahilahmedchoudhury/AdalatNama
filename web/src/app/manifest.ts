import type { MetadataRoute } from "next";

/** Web app manifest: lets juniors install AdalatNama on their phone's home screen. */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "AdalatNama",
    short_name: "AdalatNama",
    description: "Case diary and cause lists for litigation chambers.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#f6f2e9",
    theme_color: "#12343b",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
