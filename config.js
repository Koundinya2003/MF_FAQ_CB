/**
 * API base URL for FundBot frontend.
 *
 * Resolution order:
 * 1. <meta name="api-base-url" content="..."> in index.html (set at deploy time)
 * 2. Local dev hosts → http://localhost:8000
 * 3. Production (Netlify) → same-origin /api proxy (see netlify.toml)
 */
(function () {
  const LOCAL_HOSTS = new Set([
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
  ]);

  const meta = document.querySelector('meta[name="api-base-url"]');
  const metaUrl = meta && meta.getAttribute("content");
  const trimmedMeta = metaUrl && metaUrl.trim();

  if (trimmedMeta) {
    window.API_BASE_URL = trimmedMeta.replace(/\/$/, "");
    return;
  }

  if (LOCAL_HOSTS.has(window.location.hostname)) {
    window.API_BASE_URL = "http://localhost:8000";
    return;
  }

  // Production hosts — call Railway directly (CORS allowed in server.py).
  // Avoids Netlify /api proxy bandwidth limits.
  const PROD_HOSTS = new Set([
    "mf-faq.netlify.app",
    "koundinya2003.github.io",
  ]);
  if (PROD_HOSTS.has(window.location.hostname)) {
    window.API_BASE_URL = "https://mffaqcb-production.up.railway.app";
    return;
  }

  // Other deployments: try same-origin proxy first
  window.API_BASE_URL = "/api";
})();
