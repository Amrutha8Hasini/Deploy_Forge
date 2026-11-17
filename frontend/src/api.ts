// All communication with the FastAPI backend goes through this file.
// The browser calls relative URLs like /api/applications; in development Vite
// forwards them to the backend and in Docker nginx does the same.

import { navigate } from "./router";

// ---------------------------------------------------------------- types ---

export type Application = {
  id: number;
  name: string;
  repo_url: string;
  repo_owner: string;
  repo_name: string;
  branch: string;
  root_directory: string;
  project_type: string;
  created_at: string;
  current_deployment_id: number | null;
  current_url: string;
  has_token: boolean;
  container_status: string;
  latest_status: string;
  latest_version: string;
};

export type Deployment = {
  id: number;
  application_id: number;
  application_name: string;
  version: string;
  commit_id: string;
  commit_message: string;
  project_type: string;
  image_tag: string;
  container_name: string;
  host_port: number | null;
  url: string;
  build_status: string;
  status: string;
  health_status: string;
  error_message: string;
  is_rollback: boolean;
  rollback_from_version: string;
  created_at: string;
  finished_at: string | null;
  is_current: boolean;
  dockerfile?: string;
};

export type BuildLog = {
  id: number;
  step: string;
  message: string;
  level: "info" | "error" | "success";
  created_at: string;
};

export type Version = {
  id: number;
  application_id: number;
  deployment_id: number;
  version: string;
  image_tag: string;
  commit_id: string;
  created_at: string;
  image_available: boolean;
  is_current: boolean;
};

export type RepoCheck = {
  repo_owner: string;
  repo_name: string;
  branch: string;
  commit_id: string;
  commit_message: string;
  project_type: string;
  supported: boolean;
  framework: string;
  message: string;
  files_found: string[];
  dockerfile: string;
  internal_port: number;
};

export type DashboardData = {
  total_applications: number;
  successful_deployments: number;
  failed_deployments: number;
  running_containers: number;
  docker_available: boolean;
  deployments_per_day: { date: string; successful: number; failed: number }[];
  recent_deployments: Deployment[];
};

export type ContainerStats = {
  cpu_percent: number;
  memory_used_mb: number;
  memory_limit_mb: number;
  memory_percent: number;
};

export type MonitoredContainer = {
  id: string;
  name: string;
  status: string;
  image: string;
  application: string;
  version: string;
  deployment_id: number | null;
  host_port: number | null;
  url: string;
  created: string;
  stats: ContainerStats | null;
  health: string;
  health_detail: string;
};

export type SettingsData = {
  docker: {
    available: boolean;
    error?: string;
    server_version?: string;
    containers_running?: number;
    images?: number;
    os?: string;
    cpus?: number;
    memory_gb?: number;
  };
  github_token_configured: boolean;
  public_host: string;
  health_check_host: string;
  port_range: string;
  apps_network: string;
  memory_limit: string;
  cpu_limit: number;
  admin_username: string;
};

// ------------------------------------------------------- token storage ---

const TOKEN_KEY = "deployforge_token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // storage blocked (private window): the user just has to log in again
  }
}

// --------------------------------------------------------- the request ---

export class ApiError extends Error {}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (response.status === 401 && !path.endsWith("/login")) {
    setToken(null);
    navigate("/login");
    throw new ApiError("Please log in again");
  }
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((d: { msg: string }) => d.msg).join(", ");
    } catch {
      // response was not JSON
    }
    throw new ApiError(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

// ------------------------------------------------------ API functions ---

export const api = {
  login: (username: string, password: string) =>
    post<{ token: string; username: string }>("/api/auth/login", { username, password }),

  dashboard: () => request<DashboardData>("/api/dashboard"),

  checkRepository: (body: { repo_url: string; branch: string; github_token: string; root_directory: string }) =>
    post<RepoCheck>("/api/repositories/check", body),
  branches: (repo_url: string, github_token: string) =>
    post<{ branches: string[] }>("/api/repositories/branches", { repo_url, github_token }),

  applications: () => request<Application[]>("/api/applications"),
  application: (id: number) => request<Application>(`/api/applications/${id}`),
  createApplication: (body: {
    repo_url: string;
    branch: string;
    github_token: string;
    root_directory: string;
    name: string;
    project_type: string;
  }) => post<Application>("/api/applications", body),
  deleteApplication: (id: number) => request<void>(`/api/applications/${id}`, { method: "DELETE" }),
  deploy: (id: number) => post<Deployment>(`/api/applications/${id}/deploy`),
  versions: (id: number) => request<Version[]>(`/api/applications/${id}/versions`),
  rollback: (id: number, version_id: number) => post<Deployment>(`/api/applications/${id}/rollback`, { version_id }),

  deployments: (applicationId?: number) =>
    request<Deployment[]>(`/api/deployments${applicationId ? `?application_id=${applicationId}` : ""}`),
  deployment: (id: number) => request<Deployment>(`/api/deployments/${id}`),
  logs: (id: number, afterId = 0) => request<BuildLog[]>(`/api/deployments/${id}/logs?after_id=${afterId}`),

  monitoring: () =>
    request<{ docker_available: boolean; error?: string; containers: MonitoredContainer[] }>("/api/monitoring"),
  containerLogs: (name: string) => request<{ name: string; logs: string }>(`/api/containers/${name}/logs?tail=200`),
  containerAction: (name: string, action: "start" | "stop" | "restart") => post(`/api/containers/${name}/${action}`),

  settings: () => request<SettingsData>("/api/settings"),
};

// ------------------------------------------------------------- helpers ---

export function formatDate(value: string | null): string {
  if (!value) return "-";
  return new Date(value).toLocaleString(undefined, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function timeAgo(value: string): string {
  const seconds = Math.floor((Date.now() - new Date(value).getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`;
  return `${Math.floor(seconds / 86400)} d ago`;
}

export const isActive = (status: string) => status === "Pending" || status === "Deploying";
