import type { ReactNode } from "react";
import { api, timeAgo, type DashboardData } from "../api";
import { ActivityIcon, BoxIcon, CheckIcon, ExternalIcon, FolderIcon, PlusIcon, XIcon } from "../components/Icons";
import { EmptyState, ErrorBox, PageHeader, StatusBadge, TypeBadge, usePolling } from "../components/ui";
import { Link } from "../router";

function StatCard({ label, value, icon, accent }: { label: string; value: number; icon: ReactNode; accent: string }) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted">{label}</p>
        <span className={`flex h-8 w-8 items-center justify-center rounded-lg ${accent}`}>{icon}</span>
      </div>
      <p className="mt-3 text-3xl font-semibold tracking-tight text-white">{value}</p>
    </div>
  );
}

/** Simple stacked bar chart drawn with divs (no chart library needed). */
function DeploymentsChart({ days }: { days: DashboardData["deployments_per_day"] }) {
  const max = Math.max(1, ...days.map((d) => d.successful + d.failed));
  return (
    <div className="card p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-medium text-white">Deployments, last 7 days</h2>
        <div className="flex gap-3 text-xs text-muted">
          <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-sm bg-brand-violet" /> Successful</span>
          <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-sm bg-red-400" /> Failed</span>
        </div>
      </div>
      <div className="flex h-44 items-end gap-3">
        {days.map((day) => {
          const total = day.successful + day.failed;
          return (
            <div key={day.date} className="flex h-full flex-1 flex-col items-center justify-end gap-2">
              <span className="text-xs text-muted">{total || ""}</span>
              <div className="flex w-full max-w-10 flex-col justify-end overflow-hidden rounded-md" style={{ height: `${(total / max) * 100}%` }}>
                <div className="bg-red-400/80" style={{ flexGrow: day.failed }} />
                <div className="bg-gradient-to-t from-brand-blue to-brand-violet" style={{ flexGrow: day.successful }} />
              </div>
              <span className="text-xs text-muted">
                {new Date(day.date + "T00:00:00").toLocaleDateString(undefined, { weekday: "short" })}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { data, error } = usePolling(api.dashboard, 5000);
  const apps = usePolling(api.applications, 5000);

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Overview of your applications, deployments and containers."
        actions={
          <Link to="/connect" className="btn btn-primary">
            <PlusIcon /> New project
          </Link>
        }
      />
      <ErrorBox message={error} />
      {data && !data.docker_available && (
        <ErrorBox message="Docker is not reachable. Start Docker Desktop to build and run applications." />
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total applications" value={data?.total_applications ?? 0} icon={<FolderIcon />} accent="bg-blue-500/15 text-blue-300" />
        <StatCard label="Successful deployments" value={data?.successful_deployments ?? 0} icon={<CheckIcon />} accent="bg-emerald-500/15 text-emerald-300" />
        <StatCard label="Failed deployments" value={data?.failed_deployments ?? 0} icon={<XIcon />} accent="bg-red-500/15 text-red-300" />
        <StatCard label="Running containers" value={data?.running_containers ?? 0} icon={<BoxIcon />} accent="bg-violet-500/15 text-violet-300" />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2">{data && <DeploymentsChart days={data.deployments_per_day} />}</div>

        {/* Application status */}
        <div className="card p-5">
          <h2 className="mb-4 font-medium text-white">Application status</h2>
          {apps.data?.length === 0 && <p className="text-sm text-muted">No applications yet.</p>}
          <ul className="space-y-3">
            {apps.data?.slice(0, 6).map((app) => (
              <li key={app.id} className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-white">{app.name}</p>
                  <div className="mt-1 flex items-center gap-2">
                    <TypeBadge type={app.project_type} />
                    {app.latest_version && <span className="text-xs text-muted">{app.latest_version}</span>}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <StatusBadge status={app.container_status === "none" ? "Pending" : app.container_status} />
                  {app.current_url && app.container_status === "running" && (
                    <a href={app.current_url} target="_blank" rel="noreferrer" className="text-muted hover:text-white" title="Open app">
                      <ExternalIcon />
                    </a>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Recent activity */}
      <div className="card mt-6">
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <h2 className="flex items-center gap-2 font-medium text-white">
            <ActivityIcon className="h-4 w-4 text-brand-violet" /> Recent deployment activity
          </h2>
          <Link to="/history" className="text-sm text-muted hover:text-white">View all</Link>
        </div>
        {data && data.recent_deployments.length === 0 ? (
          <div className="p-5">
            <EmptyState
              title="No deployments yet"
              text="Connect a GitHub repository and click Deploy to see activity here."
              action={<Link to="/connect" className="btn btn-primary">Connect repository</Link>}
            />
          </div>
        ) : (
          <ul className="divide-y divide-line">
            {data?.recent_deployments.map((d) => (
              <li key={d.id}>
                <Link to={`/logs/${d.id}`} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3 hover:bg-surface-2/60">
                  <span className="w-10 font-mono text-xs text-muted">#{d.id}</span>
                  <span className="min-w-32 flex-1 text-sm font-medium text-white">
                    {d.application_name} <span className="text-muted">{d.version}</span>
                    {d.is_rollback && <span className="ml-2 text-xs text-amber-300">rollback</span>}
                  </span>
                  <span className="hidden font-mono text-xs text-muted sm:inline">{d.commit_id.slice(0, 7) || "-"}</span>
                  <StatusBadge status={d.status} />
                  <span className="w-20 text-right text-xs text-muted">{timeAgo(d.created_at)}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
