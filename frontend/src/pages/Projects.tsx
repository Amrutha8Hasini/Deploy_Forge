import { useState } from "react";
import { api, formatDate, type Application } from "../api";
import { BranchIcon, ExternalIcon, GitHubIcon, HistoryIcon, PlusIcon, RocketIcon, TrashIcon } from "../components/Icons";
import { EmptyState, ErrorBox, PageHeader, Spinner, StatusBadge, TypeBadge, usePolling } from "../components/ui";
import { Link, navigate } from "../router";

function ProjectCard({ app, onChanged, onError }: { app: Application; onChanged: () => void; onError: (m: string) => void }) {
  const [busy, setBusy] = useState(false);

  const deploy = async () => {
    setBusy(true);
    try {
      const deployment = await api.deploy(app.id);
      navigate(`/logs/${deployment.id}`);
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!window.confirm(`Delete ${app.name}? Its containers and images will be removed.`)) return;
    try {
      await api.deleteApplication(app.id);
      onChanged();
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="card flex flex-col p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate font-semibold text-white">{app.name}</h3>
          <a href={app.repo_url} target="_blank" rel="noreferrer" className="mt-1 flex items-center gap-1.5 truncate text-sm text-muted hover:text-white">
            <GitHubIcon className="h-3.5 w-3.5 shrink-0" /> {app.repo_owner}/{app.repo_name}
          </a>
        </div>
        <TypeBadge type={app.project_type} />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted">
        <span className="flex items-center gap-1.5"><BranchIcon className="h-3.5 w-3.5" /> {app.branch}</span>
        {app.root_directory && <span>/{app.root_directory}</span>}
        <span>Created {formatDate(app.created_at)}</span>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2 rounded-lg bg-surface-2 px-3 py-2.5 text-sm">
        <span className="text-muted">Latest:</span>
        {app.latest_version ? (
          <>
            <span className="font-medium text-white">{app.latest_version}</span>
            <StatusBadge status={app.latest_status} />
          </>
        ) : (
          <span className="text-muted">never deployed</span>
        )}
        <span className="ml-auto text-muted">Container:</span>
        <StatusBadge status={app.container_status === "none" ? "-" : app.container_status} />
      </div>

      {app.current_url && (
        <a href={app.current_url} target="_blank" rel="noreferrer" className="mt-3 flex items-center gap-1.5 font-mono text-sm text-brand-blue hover:underline">
          {app.current_url} <ExternalIcon className="h-3.5 w-3.5" />
        </a>
      )}

      <div className="mt-5 flex flex-wrap gap-2 border-t border-line pt-4">
        <button className="btn btn-primary" onClick={deploy} disabled={busy}>
          {busy ? <Spinner /> : <RocketIcon />} Deploy
        </button>
        <Link to={`/history?app=${app.id}`} className="btn btn-secondary">
          <HistoryIcon /> History
        </Link>
        <button className="btn btn-danger ml-auto" onClick={remove} title="Delete application">
          <TrashIcon />
        </button>
      </div>
    </div>
  );
}

export default function Projects() {
  const { data, error, reload } = usePolling(api.applications, 5000);
  const [actionError, setActionError] = useState("");

  return (
    <>
      <PageHeader
        title="Projects"
        description="Applications connected from GitHub."
        actions={
          <Link to="/connect" className="btn btn-primary">
            <PlusIcon /> Connect repository
          </Link>
        }
      />
      <ErrorBox message={error || actionError} />
      {data && data.length === 0 && (
        <EmptyState
          title="No projects yet"
          text="Connect a GitHub repository that contains a Python (requirements.txt) or Node.js (package.json) app."
          action={<Link to="/connect" className="btn btn-primary">Connect repository</Link>}
        />
      )}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data?.map((app) => <ProjectCard key={app.id} app={app} onChanged={reload} onError={setActionError} />)}
      </div>
    </>
  );
}
