import type { ReactNode } from "react";
import { api, setToken } from "../api";
import { LogoutIcon } from "../components/Icons";
import { ErrorBox, PageHeader, StatusBadge, usePolling } from "../components/ui";
import { navigate } from "../router";

function Row({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2.5 text-sm">
      <span className="text-muted">{label}</span>
      <span className="text-right font-mono text-gray-200">{value}</span>
    </div>
  );
}

export default function Settings() {
  const { data, error } = usePolling(api.settings, 10000);
  const docker = data?.docker;

  return (
    <>
      <PageHeader title="Settings" description="Platform configuration. Values come from the .env file on the server." />
      <ErrorBox message={error} />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="card p-5">
          <h2 className="mb-2 font-medium text-white">Docker Engine</h2>
          <div className="divide-y divide-line">
            <Row label="Status" value={<StatusBadge status={docker?.available ? "running" : "Stopped"} />} />
            {docker?.available ? (
              <>
                <Row label="Version" value={docker.server_version} />
                <Row label="Operating system" value={docker.os} />
                <Row label="CPUs / Memory" value={`${docker.cpus} CPUs / ${docker.memory_gb} GB`} />
                <Row label="Running containers (all)" value={docker.containers_running} />
                <Row label="Images" value={docker.images} />
              </>
            ) : (
              <p className="py-3 text-sm text-red-300">{docker?.error ?? "Loading..."}</p>
            )}
          </div>
        </div>

        <div className="card p-5">
          <h2 className="mb-2 font-medium text-white">Deployment settings</h2>
          <div className="divide-y divide-line">
            <Row label="App URL host" value={data?.public_host} />
            <Row label="Health check host" value={data?.health_check_host} />
            <Row label="Host port range" value={data?.port_range} />
            <Row label="Apps network" value={data?.apps_network} />
            <Row label="Memory limit per app" value={data?.memory_limit} />
            <Row label="CPU limit per app" value={data ? `${data.cpu_limit} CPU` : ""} />
          </div>
        </div>

        <div className="card p-5">
          <h2 className="mb-2 font-medium text-white">GitHub</h2>
          <div className="divide-y divide-line">
            <Row label="Default token (GITHUB_TOKEN)" value={<StatusBadge status={data?.github_token_configured ? "Successful" : "Stopped"} />} />
          </div>
          <p className="mt-3 text-sm text-muted">
            Public repositories need no token. For private ones, add a token per application on the Connect Repository page,
            or set <span className="font-mono text-gray-300">GITHUB_TOKEN</span> in <span className="font-mono text-gray-300">.env</span> and restart the backend.
          </p>
        </div>

        <div className="card p-5">
          <h2 className="mb-2 font-medium text-white">Account</h2>
          <div className="divide-y divide-line">
            <Row label="Signed in as" value={data?.admin_username} />
          </div>
          <p className="mt-3 text-sm text-muted">
            Change the username and password with <span className="font-mono text-gray-300">ADMIN_USERNAME</span> and{" "}
            <span className="font-mono text-gray-300">ADMIN_PASSWORD</span> in <span className="font-mono text-gray-300">.env</span>.
          </p>
          <button
            className="btn btn-danger mt-4"
            onClick={() => {
              setToken(null);
              navigate("/login");
            }}
          >
            <LogoutIcon /> Log out
          </button>
        </div>
      </div>
    </>
  );
}
