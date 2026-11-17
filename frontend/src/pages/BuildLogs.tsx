import { useEffect, useRef, useState } from "react";
import { api, formatDate, isActive, timeAgo, type BuildLog, type Deployment } from "../api";
import { CheckIcon, CommitIcon, ExternalIcon, XIcon } from "../components/Icons";
import { EmptyState, ErrorBox, PageHeader, Spinner, StatusBadge, usePolling } from "../components/ui";
import { Link } from "../router";

const BUILD_STEPS = [
  ["clone", "Fetch"],
  ["detect", "Detect"],
  ["dockerfile", "Dockerfile"],
  ["build", "Build image"],
  ["run", "Start container"],
  ["health", "Health check"],
  ["done", "Live"],
];
const ROLLBACK_STEPS = [
  ["rollback", "Find image"],
  ["run", "Start container"],
  ["health", "Health check"],
  ["done", "Live"],
];

/** Work out whether each pipeline step is done, running, failed or waiting. */
function stepStates(steps: string[][], logs: BuildLog[], deployment: Deployment) {
  const seen = logs.map((l) => l.step);
  const lastStepIndex = Math.max(-1, ...seen.map((s) => steps.findIndex(([key]) => key === s)));
  const failed = deployment.status === "Failed";
  return steps.map(([key], index) => {
    if (deployment.status === "Successful" || index < lastStepIndex) return "done";
    if (index === lastStepIndex) return failed ? "failed" : isActive(deployment.status) ? "active" : "done";
    if (index === lastStepIndex + 1 && failed && lastStepIndex === -1) return "failed";
    return "waiting";
  });
}

function Pipeline({ deployment, logs }: { deployment: Deployment; logs: BuildLog[] }) {
  const steps = deployment.is_rollback ? ROLLBACK_STEPS : BUILD_STEPS;
  const states = stepStates(steps, logs, deployment);
  return (
    <div className="card mb-6 overflow-x-auto p-5">
      <ol className="flex min-w-[640px] items-center">
        {steps.map(([key, label], index) => {
          const state = states[index];
          const circle =
            state === "done"
              ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
              : state === "active"
                ? "bg-blue-500/15 text-blue-300 border-blue-500/40"
                : state === "failed"
                  ? "bg-red-500/15 text-red-300 border-red-500/40"
                  : "bg-surface-2 text-muted border-line";
          return (
            <li key={key} className="flex flex-1 items-center last:flex-none">
              <div className="flex flex-col items-center gap-2">
                <span className={`flex h-8 w-8 items-center justify-center rounded-full border text-xs ${circle}`}>
                  {state === "done" ? <CheckIcon /> : state === "failed" ? <XIcon /> : state === "active" ? <Spinner className="h-3.5 w-3.5" /> : index + 1}
                </span>
                <span className={`whitespace-nowrap text-xs ${state === "waiting" ? "text-muted" : "text-gray-200"}`}>{label}</span>
              </div>
              {index < steps.length - 1 && (
                <div className={`mx-2 mb-6 h-px flex-1 ${states[index + 1] !== "waiting" ? "bg-emerald-500/40" : "bg-line"}`} />
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function DeploymentPicker() {
  const { data, error } = usePolling(() => api.deployments(), 5000);
  return (
    <>
      <PageHeader title="Build Logs" description="Choose a deployment to see its live build and deployment logs." />
      <ErrorBox message={error} />
      {data?.length === 0 && <EmptyState title="No deployments yet" text="Logs appear here after you click Deploy." />}
      <div className="card divide-y divide-line">
        {data?.map((d) => (
          <Link key={d.id} to={`/logs/${d.id}`} className="flex flex-wrap items-center gap-4 px-5 py-3 hover:bg-surface-2/60">
            <span className="font-mono text-xs text-muted">#{d.id}</span>
            <span className="flex-1 text-sm font-medium text-white">
              {d.application_name} <span className="text-muted">{d.version}</span>
            </span>
            <StatusBadge status={d.status} />
            <span className="text-xs text-muted">{timeAgo(d.created_at)}</span>
          </Link>
        ))}
      </div>
    </>
  );
}

export default function BuildLogs({ deploymentId }: { deploymentId: number | null }) {
  const [deployment, setDeployment] = useState<Deployment | null>(null);
  const [logs, setLogs] = useState<BuildLog[]>([]);
  const [tab, setTab] = useState<"logs" | "dockerfile">("logs");
  const [error, setError] = useState("");
  const lastLogId = useRef(0);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Poll the deployment and its new log lines every 1.5 seconds until it finishes
  useEffect(() => {
    if (!deploymentId) return;
    setDeployment(null);
    setLogs([]);
    lastLogId.current = 0;
    let stopped = false;
    let timer = 0;

    const poll = async () => {
      try {
        const [current, newLogs] = await Promise.all([api.deployment(deploymentId), api.logs(deploymentId, lastLogId.current)]);
        if (stopped) return;
        if (newLogs.length) {
          lastLogId.current = newLogs[newLogs.length - 1].id;
          setLogs((old) => [...old, ...newLogs]);
        }
        setDeployment(current);
        setError("");
        if (isActive(current.status)) timer = window.setTimeout(poll, 1500);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        timer = window.setTimeout(poll, 3000);
      }
    };
    poll();
    return () => {
      stopped = true;
      window.clearTimeout(timer);
    };
  }, [deploymentId]);

  // Keep the newest log line visible
  useEffect(() => {
    if (deployment && isActive(deployment.status)) bottomRef.current?.scrollIntoView({ block: "nearest" });
  }, [logs, deployment]);

  if (!deploymentId) return <DeploymentPicker />;

  const lineColor = (level: string) =>
    level === "error" ? "text-red-300" : level === "success" ? "text-emerald-300" : "text-gray-300";

  return (
    <>
      <PageHeader
        title={deployment ? `${deployment.application_name} · ${deployment.version}` : "Build Logs"}
        description={deployment ? `Deployment #${deployment.id} · started ${formatDate(deployment.created_at)}` : "Loading..."}
        actions={
          <>
            <Link to="/logs" className="btn btn-secondary">All deployments</Link>
            {deployment?.status === "Successful" && deployment.is_current && (
              <a href={deployment.url} target="_blank" rel="noreferrer" className="btn btn-primary">
                <ExternalIcon /> Open application
              </a>
            )}
          </>
        }
      />
      <ErrorBox message={error} />

      {deployment && (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-3 text-sm">
            <span className="text-muted">Build</span> <StatusBadge status={deployment.build_status} />
            <span className="ml-2 text-muted">Deployment</span> <StatusBadge status={deployment.status} />
            <span className="ml-2 text-muted">Health</span> <StatusBadge status={deployment.health_status} />
            {deployment.commit_id && (
              <span className="flex items-center gap-1.5 text-muted">
                <CommitIcon className="h-4 w-4" />
                <span className="font-mono text-gray-300">{deployment.commit_id.slice(0, 7)}</span> {deployment.commit_message}
              </span>
            )}
            {deployment.is_rollback && <span className="text-amber-300">Rollback from {deployment.rollback_from_version || "-"}</span>}
          </div>

          <Pipeline deployment={deployment} logs={logs} />

          {deployment.status === "Failed" && deployment.error_message && <ErrorBox message={deployment.error_message} />}
          {deployment.status === "Successful" && (
            <div className="mb-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
              Deployed successfully. Image <span className="font-mono">{deployment.image_tag}</span> is running in container{" "}
              <span className="font-mono">{deployment.container_name}</span> at{" "}
              <a href={deployment.url} target="_blank" rel="noreferrer" className="font-mono underline">{deployment.url}</a>.
            </div>
          )}
        </>
      )}

      <div className="card overflow-hidden">
        <div className="flex border-b border-line">
          {(["logs", "dockerfile"] as const).map((name) => (
            <button
              key={name}
              onClick={() => setTab(name)}
              className={`px-5 py-3 text-sm font-medium ${tab === name ? "border-b-2 border-brand-violet text-white" : "text-muted hover:text-white"}`}
            >
              {name === "logs" ? `Logs (${logs.length})` : "Dockerfile"}
            </button>
          ))}
        </div>
        {tab === "logs" ? (
          <div className="max-h-[560px] overflow-auto bg-black/50 p-4 font-mono text-xs leading-relaxed">
            {logs.length === 0 && <p className="text-muted">Waiting for logs...</p>}
            {logs.map((line) => (
              <div key={line.id} className="flex gap-3">
                <span className="w-20 shrink-0 select-none text-muted/60">{new Date(line.created_at).toLocaleTimeString()}</span>
                <span className="w-20 shrink-0 select-none text-brand-violet/80">[{line.step}]</span>
                <span className={`whitespace-pre-wrap break-all ${lineColor(line.level)}`}>{line.message}</span>
              </div>
            ))}
            {deployment && isActive(deployment.status) && (
              <div className="mt-2 flex items-center gap-2 text-blue-300"><Spinner className="h-3 w-3" /> running...</div>
            )}
            <div ref={bottomRef} />
          </div>
        ) : (
          <pre className="max-h-[560px] overflow-auto bg-black/50 p-5 font-mono text-xs leading-relaxed text-gray-300">
            {deployment?.dockerfile || "Dockerfile not generated yet."}
          </pre>
        )}
      </div>
    </>
  );
}
