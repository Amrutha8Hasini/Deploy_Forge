import { useState } from "react";
import { api, type MonitoredContainer } from "../api";
import { ExternalIcon, PlayIcon, RestartIcon, StopIcon, TerminalIcon, XIcon } from "../components/Icons";
import { EmptyState, ErrorBox, PageHeader, ProgressBar, Spinner, StatusBadge, usePolling } from "../components/ui";

function ContainerCard({
  container,
  onAction,
  onShowLogs,
  busy,
}: {
  container: MonitoredContainer;
  onAction: (name: string, action: "start" | "stop" | "restart") => void;
  onShowLogs: (name: string) => void;
  busy: boolean;
}) {
  const running = container.status === "running";
  const stats = container.stats;
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-semibold text-white">
            {container.application} <span className="text-muted">{container.version}</span>
          </p>
          <p className="mt-0.5 truncate font-mono text-xs text-muted" title={container.name}>{container.name}</p>
        </div>
        <StatusBadge status={container.status} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4">
        <div>
          <div className="mb-1.5 flex justify-between text-xs">
            <span className="text-muted">CPU</span>
            <span className="font-mono text-gray-200">{stats ? `${stats.cpu_percent.toFixed(1)}%` : "-"}</span>
          </div>
          <ProgressBar value={stats?.cpu_percent ?? 0} />
        </div>
        <div>
          <div className="mb-1.5 flex justify-between text-xs">
            <span className="text-muted">Memory</span>
            <span className="font-mono text-gray-200">
              {stats ? `${stats.memory_used_mb} / ${stats.memory_limit_mb} MB` : "-"}
            </span>
          </div>
          <ProgressBar value={stats?.memory_percent ?? 0} color="from-emerald-500 to-teal-400" />
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
        <span className="text-muted">Health</span>
        <StatusBadge status={container.health} />
        {container.health_detail && <span className="font-mono text-muted">{container.health_detail}</span>}
      </div>
      {container.url && (
        <a href={container.url} target="_blank" rel="noreferrer" className="mt-2 flex items-center gap-1 font-mono text-sm text-brand-blue hover:underline">
          {container.url} <ExternalIcon className="h-3.5 w-3.5" />
        </a>
      )}

      <div className="mt-4 flex flex-wrap gap-2 border-t border-line pt-4">
        {running ? (
          <button className="btn btn-secondary" disabled={busy} onClick={() => onAction(container.name, "stop")}>
            <StopIcon /> Stop
          </button>
        ) : (
          <button className="btn btn-secondary" disabled={busy} onClick={() => onAction(container.name, "start")}>
            <PlayIcon /> Start
          </button>
        )}
        <button className="btn btn-secondary" disabled={busy} onClick={() => onAction(container.name, "restart")}>
          <RestartIcon /> Restart
        </button>
        <button className="btn btn-secondary" onClick={() => onShowLogs(container.name)}>
          <TerminalIcon /> Logs
        </button>
        {busy && <Spinner className="ml-auto h-4 w-4 self-center text-muted" />}
      </div>
    </div>
  );
}

export default function Monitoring() {
  const { data, error, reload } = usePolling(api.monitoring, 5000);
  const [busyName, setBusyName] = useState("");
  const [actionError, setActionError] = useState("");
  const [logName, setLogName] = useState("");
  const [logText, setLogText] = useState("");

  const doAction = async (name: string, action: "start" | "stop" | "restart") => {
    setBusyName(name);
    setActionError("");
    try {
      await api.containerAction(name, action);
      await reload();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyName("");
    }
  };

  const showLogs = async (name: string) => {
    setLogName(name);
    setLogText("Loading...");
    try {
      setLogText((await api.containerLogs(name)).logs || "(no output yet)");
    } catch (err) {
      setLogText(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <>
      <PageHeader title="Monitoring" description="Live container status, CPU, memory and health. Refreshes every 5 seconds." />
      <ErrorBox message={error || actionError || (data && !data.docker_available ? data.error ?? "Docker is not reachable" : "")} />
      {data?.containers.length === 0 && (
        <EmptyState title="No containers" text="Deployed applications will appear here with their resource usage." />
      )}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {data?.containers.map((c) => (
          <ContainerCard key={c.name} container={c} onAction={doAction} onShowLogs={showLogs} busy={busyName === c.name} />
        ))}
      </div>

      {logName && (
        <div className="card mt-6 overflow-hidden">
          <div className="flex items-center justify-between border-b border-line px-5 py-3">
            <p className="text-sm font-medium text-white">
              Logs: <span className="font-mono text-muted">{logName}</span>
            </p>
            <div className="flex gap-2">
              <button className="btn btn-secondary py-1.5 text-xs" onClick={() => showLogs(logName)}>
                <RestartIcon className="h-3.5 w-3.5" /> Refresh
              </button>
              <button className="btn btn-secondary py-1.5 text-xs" onClick={() => setLogName("")} aria-label="Close logs">
                <XIcon className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
          <pre className="max-h-96 overflow-auto whitespace-pre-wrap bg-black/50 p-4 font-mono text-xs leading-relaxed text-gray-300">{logText}</pre>
        </div>
      )}
    </>
  );
}
