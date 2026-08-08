/**
 * Resolves the FundBot API base URL.
 *
 * Order:
 *   1. <meta name="api-base-url"> — explicit override, for pointing a static
 *      host at an API deployed somewhere else.
 *   2. A local page served from anything other than the Flask dev port — assume
 *      the API is the Flask server on :8000.
 *   3. Same origin — the default. On Vercel the static files and the Python
 *      functions share a domain, so /api needs no CORS at all.
 */
(function () {
  "use strict";

  var FLASK_DEV_PORT = "8000";
  var LOCAL_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", ""];

  function trimTrailingSlash(value) {
    return value.replace(/\/+$/, "");
  }

  var meta = document.querySelector('meta[name="api-base-url"]');
  var override = meta && meta.getAttribute("content");
  if (override && override.trim()) {
    window.API_BASE_URL = trimTrailingSlash(override.trim());
    return;
  }

  var isLocal = LOCAL_HOSTS.indexOf(window.location.hostname) !== -1;
  if (isLocal && window.location.port !== FLASK_DEV_PORT) {
    // Static page on a different port (Live Server, `python -m http.server`, …)
    // while the API runs on the Flask default.
    window.API_BASE_URL = "http://localhost:" + FLASK_DEV_PORT + "/api";
    return;
  }

  window.API_BASE_URL = "/api";
})();
