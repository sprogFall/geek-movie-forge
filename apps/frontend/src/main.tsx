import { StrictMode } from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";

import "@/app/globals.css";
import { App } from "./app";

const STATIC_FILE_PATH_RE = /\.[a-zA-Z0-9]+$/;

function normalizeDirectRouteToHashUrl() {
  const { hash, pathname, search } = window.location;
  if (hash || pathname === "/" || pathname.startsWith("/_assets/") || STATIC_FILE_PATH_RE.test(pathname)) {
    return;
  }

  window.history.replaceState(null, "", `/#${pathname}${search}`);
}

normalizeDirectRouteToHashUrl();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </StrictMode>,
);
