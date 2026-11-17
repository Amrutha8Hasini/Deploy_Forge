// Page frame: sidebar navigation on the left, page content on the right.
// On small screens the sidebar becomes a slide-in menu.

import { useState, type ReactNode } from "react";
import { setToken } from "../api";
import { Link, navigate } from "../router";
import {
  ActivityIcon,
  DashboardIcon,
  FolderIcon,
  GitHubIcon,
  HistoryIcon,
  LogoutIcon,
  MenuIcon,
  RocketIcon,
  SettingsIcon,
  TerminalIcon,
} from "./Icons";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: DashboardIcon },
  { to: "/projects", label: "Projects", icon: FolderIcon },
  { to: "/connect", label: "Connect Repository", icon: GitHubIcon },
  { to: "/deploy", label: "Create Deployment", icon: RocketIcon },
  { to: "/logs", label: "Build Logs", icon: TerminalIcon },
  { to: "/history", label: "Deployment History", icon: HistoryIcon },
  { to: "/monitoring", label: "Monitoring", icon: ActivityIcon },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

export function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <img src="/logo.svg" alt="" className="h-8 w-8" />
      <span className="text-[17px] font-semibold tracking-tight text-white">DeployForge</span>
    </div>
  );
}

export default function Layout({ path, children }: { path: string; children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);

  const isActive = (to: string) => (to === "/" ? path === "/" : path.startsWith(to));

  const logout = () => {
    setToken(null);
    navigate("/login");
  };

  const sidebar = (
    <nav className="flex h-full flex-col border-r border-line bg-surface/80 px-3 py-5">
      <div className="px-2 pb-6">
        <Logo />
      </div>
      <div className="flex flex-1 flex-col gap-0.5">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <div key={to} onClick={() => setMenuOpen(false)}>
            <Link
              to={to}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                isActive(to)
                  ? "bg-gradient-to-r from-brand-blue/15 to-brand-violet/15 text-white ring-1 ring-brand/30"
                  : "text-muted hover:bg-surface-2 hover:text-white"
              }`}
            >
              <Icon className={`h-4 w-4 ${isActive(to) ? "text-brand-violet" : ""}`} />
              {label}
            </Link>
          </div>
        ))}
      </div>
      <button onClick={logout} className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted hover:bg-surface-2 hover:text-white">
        <LogoutIcon className="h-4 w-4" /> Log out
      </button>
    </nav>
  );

  return (
    <div className="flex h-full">
      {/* Desktop sidebar */}
      <aside className="hidden w-64 shrink-0 lg:block">{sidebar}</aside>

      {/* Mobile sidebar */}
      {menuOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setMenuOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-64">{sidebar}</aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-line px-4 py-3 lg:hidden">
          <Logo />
          <button className="btn btn-secondary px-2.5" onClick={() => setMenuOpen(true)} aria-label="Open menu">
            <MenuIcon />
          </button>
        </header>
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
