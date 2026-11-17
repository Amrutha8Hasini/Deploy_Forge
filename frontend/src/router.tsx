// A very small router (about 40 lines) so that we do not need an extra
// library. It uses the browser History API: navigate() changes the URL
// without reloading the page, and useRoute() re-renders on every change.

import { useEffect, useState, type MouseEvent, type ReactNode } from "react";

const ROUTE_EVENT = "deployforge:navigate";

export function navigate(to: string) {
  if (window.location.pathname + window.location.search !== to) {
    window.history.pushState({}, "", to);
  }
  window.dispatchEvent(new Event(ROUTE_EVENT));
}

/** Returns the current path (e.g. "/logs/5") and query parameters. */
export function useRoute() {
  const [location, setLocation] = useState(() => ({
    path: window.location.pathname,
    query: new URLSearchParams(window.location.search),
  }));

  useEffect(() => {
    const update = () =>
      setLocation({ path: window.location.pathname, query: new URLSearchParams(window.location.search) });
    window.addEventListener("popstate", update); // browser back/forward buttons
    window.addEventListener(ROUTE_EVENT, update);
    return () => {
      window.removeEventListener("popstate", update);
      window.removeEventListener(ROUTE_EVENT, update);
    };
  }, []);

  return location;
}

export function Link({ to, className, children }: { to: string; className?: string; children: ReactNode }) {
  const onClick = (event: MouseEvent<HTMLAnchorElement>) => {
    if (event.metaKey || event.ctrlKey) return; // allow "open in new tab"
    event.preventDefault();
    navigate(to);
  };
  return (
    <a href={to} onClick={onClick} className={className}>
      {children}
    </a>
  );
}
