import { useEffect, useState } from "react";
import { api } from "../api";
import { BranchIcon, GitHubIcon, RocketIcon } from "../components/Icons";
import { EmptyState, ErrorBox, PageHeader, Spinner, StatusBadge, TypeBadge, usePolling } from "../components/ui";
import { Link, navigate } from "../router";

// The steps the backend performs, shown so the user knows what will happen
const PIPELINE = [
  ["Fetch repository", "git clone of the selected branch"],
  ["Detect project type", "requirements.txt or package.json"],
  ["Generate Dockerfile", "from a Python or Node.js template"],
  ["Build Docker image", "real build logs are captured"],
  ["Save deployment", "version, commit and image tag"],
  ["Start container", "on a free local port (8100+)"],
  ["Health check", "GET /health, then GET /"],
  ["Go live", "old version is stopped only if the new one is healthy"],
];

export default function CreateDeployment({ preselectedId }: { preselectedId: number | null }) {
  const { data: apps, error } = usePolling(api.applications);
  const [selectedId, setSelectedId] = useState<number | null>(preselectedId);
  const [deploying, setDeploying] = useState(false);
  const [deployError, setDeployError] = useState("");

  // Pick the first application automatically when none is selected
  useEffect(() => {
    if (!selectedId && apps?.length) setSelectedId(apps[0].id);
  }, [apps, selectedId]);

  const selected = apps?.find((a) => a.id === selectedId) ?? null;

  const deploy = async () => {
    if (!selected) return;
    setDeploying(true);
    setDeployError("");
    try {
      const deployment = await api.deploy(selected.id);
      navigate(`/logs/${deployment.id}`);
    } catch (err) {
      setDeployError(err instanceof Error ? err.message : String(err));
      setDeploying(false);
    }
  };

  if (apps && apps.length === 0) {
    return (
      <>
        <PageHeader title="Create Deployment" />
        <EmptyState
          title="Nothing to deploy yet"
          text="Connect a GitHub repository first."
          action={<Link to="/connect" className="btn btn-primary">Connect repository</Link>}
        />
      </>
    );
  }

  return (
    <>
      <PageHeader title="Create Deployment" description="Build the latest commit and run it in a Docker container." />
      <ErrorBox message={error || deployError} />
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
        <div className="card p-6 xl:col-span-3">
          <label className="label" htmlFor="app">Application</label>
          <select id="app" className="input mb-6" value={selectedId ?? ""} onChange={(e) => setSelectedId(Number(e.target.value))}>
            {apps?.map((app) => (
              <option key={app.id} value={app.id}>
                {app.name}
              </option>
            ))}
          </select>

          {selected && (
            <div className="rounded-xl border border-line bg-surface-2/60 p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-lg font-semibold text-white">{selected.name}</p>
                  <p className="mt-1 flex items-center gap-1.5 text-sm text-muted">
                    <GitHubIcon className="h-3.5 w-3.5" /> {selected.repo_owner}/{selected.repo_name}
                  </p>
                </div>
                <TypeBadge type={selected.project_type} />
              </div>
              <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-muted">Branch</dt>
                  <dd className="mt-0.5 flex items-center gap-1.5 text-white"><BranchIcon className="h-3.5 w-3.5" /> {selected.branch}</dd>
                </div>
                <div>
                  <dt className="text-muted">Root directory</dt>
                  <dd className="mt-0.5 text-white">/{selected.root_directory}</dd>
                </div>
                <div>
                  <dt className="text-muted">Current version</dt>
                  <dd className="mt-0.5 text-white">{selected.latest_version || "none"}</dd>
                </div>
                <div>
                  <dt className="text-muted">Last status</dt>
                  <dd className="mt-0.5">{selected.latest_status ? <StatusBadge status={selected.latest_status} /> : "-"}</dd>
                </div>
              </dl>
            </div>
          )}

          <button className="btn btn-primary mt-6 w-full py-3 text-base" onClick={deploy} disabled={!selected || deploying}>
            {deploying ? <Spinner /> : <RocketIcon className="h-5 w-5" />} Deploy
          </button>
        </div>

        <div className="card p-6 xl:col-span-2">
          <h2 className="mb-4 font-medium text-white">Deployment pipeline</h2>
          <ol className="relative space-y-4 border-l border-line pl-6">
            {PIPELINE.map(([title, detail], index) => (
              <li key={title}>
                <span className="absolute -left-3 flex h-6 w-6 items-center justify-center rounded-full border border-line bg-surface text-xs text-muted">
                  {index + 1}
                </span>
                <p className="text-sm font-medium text-white">{title}</p>
                <p className="text-xs text-muted">{detail}</p>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </>
  );
}
