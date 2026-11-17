import { useEffect, useState } from "react";
import { api, formatDate } from "../api";
import { ExternalIcon, HistoryIcon } from "../components/Icons";
import { EmptyState, ErrorBox, PageHeader, Spinner, StatusBadge, usePolling } from "../components/ui";
import { Link, navigate } from "../router";

/** Successful versions of one application, each with a Rollback button. */
function RollbackPanel({ applicationId }: { applicationId: number }) {
  const { data: versions, error, reload } = usePolling(() => api.versions(applicationId), 5000, [applicationId]);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [actionError, setActionError] = useState("");

  const rollback = async (versionId: number, label: string) => {
    if (!window.confirm(`Roll back to ${label}? The current version will be stopped.`)) return;
    setBusyId(versionId);
    setActionError("");
    try {
      const deployment = await api.rollback(applicationId, versionId);
      navigate(`/logs/${deployment.id}`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
      setBusyId(null);
      reload();
    }
  };

  return (
    <div className="card mb-6 p-5">
      <h2 className="mb-1 flex items-center gap-2 font-medium text-white">
        <HistoryIcon className="h-4 w-4 text-brand-violet" /> Rollback
      </h2>
      <p className="mb-4 text-sm text-muted">
        Every version that built and passed its health check is kept as a Docker image. Rolling back starts that image in a new container.
      </p>
      <ErrorBox message={error || actionError} />
      {versions?.length === 0 && <p className="text-sm text-muted">No successful versions yet.</p>}
      <div className="flex flex-wrap gap-3">
        {versions?.map((v) => (
          <div key={v.id} className={`min-w-48 rounded-lg border px-4 py-3 ${v.is_current ? "border-brand/50 bg-brand/10" : "border-line bg-surface-2/60"}`}>
            <div className="flex items-center justify-between gap-3">
              <span className="font-semibold text-white">{v.version}</span>
              {v.is_current && <span className="text-xs text-brand-violet">live</span>}
            </div>
            <p className="mt-1 font-mono text-xs text-muted">{v.commit_id.slice(0, 7) || "-"} · {formatDate(v.created_at)}</p>
            <p className="mt-0.5 truncate font-mono text-xs text-muted" title={v.image_tag}>{v.image_tag}</p>
            {!v.is_current && (
              <button
                className="btn btn-secondary mt-3 w-full py-1.5 text-xs"
                disabled={!v.image_available || busyId !== null}
                onClick={() => rollback(v.id, v.version)}
                title={v.image_available ? "" : "Image was deleted"}
              >
                {busyId === v.id ? <Spinner className="h-3 w-3" /> : null}
                {v.image_available ? `Roll back to ${v.version}` : "Image missing"}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function DeploymentHistory({ preselectedId }: { preselectedId: number | null }) {
  const { data: apps } = usePolling(api.applications);
  const [applicationId, setApplicationId] = useState<number | null>(preselectedId);
  const { data: deployments, error } = usePolling(() => api.deployments(applicationId ?? undefined), 4000, [applicationId]);

  // When there is only one application, select it so the rollback panel shows
  useEffect(() => {
    if (applicationId === null && apps?.length === 1) setApplicationId(apps[0].id);
  }, [apps, applicationId]);

  return (
    <>
      <PageHeader
        title="Deployment History"
        description="Every deployment with its version, commit and result."
        actions={
          <select className="input w-56" value={applicationId ?? ""} onChange={(e) => setApplicationId(e.target.value ? Number(e.target.value) : null)}>
            <option value="">All applications</option>
            {apps?.map((app) => <option key={app.id} value={app.id}>{app.name}</option>)}
          </select>
        }
      />
      <ErrorBox message={error} />
      {applicationId ? <RollbackPanel applicationId={applicationId} /> : (
        <p className="mb-4 text-sm text-muted">Select an application to see its versions and roll back.</p>
      )}

      {deployments?.length === 0 ? (
        <EmptyState title="No deployments" text="Deployments will be listed here." />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[900px]">
            <thead className="border-b border-line">
              <tr>
                <th className="table-head">ID</th>
                <th className="table-head">Application</th>
                <th className="table-head">Version</th>
                <th className="table-head">Commit</th>
                <th className="table-head">Date &amp; time</th>
                <th className="table-head">Build</th>
                <th className="table-head">Deployment</th>
                <th className="table-head">URL</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {deployments?.map((d) => (
                <tr key={d.id} className="hover:bg-surface-2/50">
                  <td className="table-cell font-mono text-muted">
                    <Link to={`/logs/${d.id}`} className="hover:text-white">#{d.id}</Link>
                  </td>
                  <td className="table-cell font-medium text-white">{d.application_name}</td>
                  <td className="table-cell">
                    <span className="text-white">{d.version}</span>
                    {d.is_rollback && <span className="ml-2 rounded bg-amber-500/10 px-1.5 py-0.5 text-xs text-amber-300">rollback</span>}
                    {d.is_current && <span className="ml-2 rounded bg-brand/15 px-1.5 py-0.5 text-xs text-brand-violet">live</span>}
                  </td>
                  <td className="table-cell font-mono text-xs text-muted" title={d.commit_message}>{d.commit_id.slice(0, 7) || "-"}</td>
                  <td className="table-cell text-muted">{formatDate(d.created_at)}</td>
                  <td className="table-cell"><StatusBadge status={d.build_status} /></td>
                  <td className="table-cell"><StatusBadge status={d.status} /></td>
                  <td className="table-cell">
                    {d.url && d.is_current ? (
                      <a href={d.url} target="_blank" rel="noreferrer" className="flex items-center gap-1 font-mono text-xs text-brand-blue hover:underline">
                        {d.url.replace("http://", "")} <ExternalIcon className="h-3 w-3" />
                      </a>
                    ) : (
                      <span className="font-mono text-xs text-muted">{d.url ? d.url.replace("http://", "") : "-"}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
