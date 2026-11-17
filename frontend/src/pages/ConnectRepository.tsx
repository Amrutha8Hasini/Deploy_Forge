import { useState, type FormEvent } from "react";
import { api, type RepoCheck } from "../api";
import { BranchIcon, CheckIcon, CommitIcon, GitHubIcon } from "../components/Icons";
import { ErrorBox, PageHeader, Spinner, TypeBadge } from "../components/ui";
import { navigate } from "../router";

export default function ConnectRepository() {
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [rootDirectory, setRootDirectory] = useState("");
  const [token, setToken] = useState("");
  const [name, setName] = useState("");
  const [branches, setBranches] = useState<string[]>([]);

  const [check, setCheck] = useState<RepoCheck | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState<"" | "check" | "branches" | "save">("");

  const run = async (kind: typeof loading, action: () => Promise<void>) => {
    setLoading(kind);
    setError("");
    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading("");
    }
  };

  // Step 1: fetch the repository and detect the project type
  const fetchRepository = (event: FormEvent) => {
    event.preventDefault();
    setCheck(null);
    run("check", async () => {
      setCheck(await api.checkRepository({ repo_url: repoUrl, branch, github_token: token, root_directory: rootDirectory }));
    });
  };

  const loadBranches = () =>
    run("branches", async () => {
      const result = await api.branches(repoUrl, token);
      setBranches(result.branches);
      if (result.branches.length && !result.branches.includes(branch)) setBranch(result.branches[0]);
    });

  // Step 2: save it as an application
  const save = () =>
    run("save", async () => {
      const app = await api.createApplication({
        repo_url: repoUrl,
        branch,
        github_token: token,
        root_directory: rootDirectory,
        name: name || check?.repo_name || "",
        project_type: check?.project_type ?? "unknown",
      });
      navigate(`/deploy?app=${app.id}`);
    });

  return (
    <>
      <PageHeader title="Connect Repository" description="Fetch a GitHub repository, detect its type and preview the generated Dockerfile." />
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
        <form onSubmit={fetchRepository} className="card p-6 xl:col-span-3">
          <ErrorBox message={error} />
          <label className="label" htmlFor="repo">GitHub repository URL</label>
          <div className="relative mb-4">
            <GitHubIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              id="repo"
              className="input pl-9"
              placeholder="https://github.com/your-name/your-app"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              required
            />
          </div>

          <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="branch">Branch</label>
              <div className="flex gap-2">
                <input id="branch" className="input" list="branch-list" value={branch} onChange={(e) => setBranch(e.target.value)} required />
                <datalist id="branch-list">
                  {branches.map((b) => <option key={b} value={b} />)}
                </datalist>
                <button type="button" className="btn btn-secondary shrink-0" onClick={loadBranches} disabled={!repoUrl || loading !== ""}>
                  {loading === "branches" ? <Spinner /> : <BranchIcon />} Load
                </button>
              </div>
            </div>
            <div>
              <label className="label" htmlFor="root-dir">Root directory (optional)</label>
              <input id="root-dir" className="input" placeholder="e.g. sample-app" value={rootDirectory} onChange={(e) => setRootDirectory(e.target.value)} />
            </div>
          </div>

          <label className="label" htmlFor="token">GitHub Personal Access Token (only for private repositories)</label>
          <input
            id="token"
            type="password"
            className="input mb-4"
            placeholder="github_pat_... or ghp_..."
            value={token}
            onChange={(e) => setToken(e.target.value)}
            autoComplete="off"
          />

          <label className="label" htmlFor="name">Application name (optional)</label>
          <input id="name" className="input mb-6" placeholder="Defaults to the repository name" value={name} onChange={(e) => setName(e.target.value)} />

          <button type="submit" className="btn btn-primary" disabled={loading !== ""}>
            {loading === "check" ? <Spinner /> : <GitHubIcon />} Fetch &amp; detect
          </button>
        </form>

        {/* Help panel */}
        <div className="card h-fit p-6 text-sm text-muted xl:col-span-2">
          <h2 className="mb-3 font-medium text-white">How it works</h2>
          <ol className="list-decimal space-y-2 pl-5">
            <li>DeployForge clones the latest commit of the branch with <span className="font-mono text-gray-300">git</span>.</li>
            <li><span className="font-mono text-gray-300">requirements.txt</span> means Python, <span className="font-mono text-gray-300">package.json</span> means Node.js.</li>
            <li>A Dockerfile is generated for the detected type. Your own Dockerfile is never overwritten.</li>
          </ol>
          <h2 className="mb-2 mt-5 font-medium text-white">Private repository?</h2>
          <p>
            GitHub → Settings → Developer settings → Personal access tokens → Fine-grained token. Give it
            <span className="text-gray-300"> read-only “Contents”</span> access to the repository and paste it above.
          </p>
          <h2 className="mb-2 mt-5 font-medium text-white">App requirements</h2>
          <p>
            The app must listen on <span className="font-mono text-gray-300">0.0.0.0</span> and the port in the
            <span className="font-mono text-gray-300"> PORT</span> variable (8000 for Python, 3000 for Node.js).
          </p>
        </div>
      </div>

      {check && (
        <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-5">
          <div className="card p-6 xl:col-span-2">
            <h2 className="mb-4 font-medium text-white">Repository</h2>
            <p className="flex items-center gap-2 text-lg font-semibold text-white">
              <GitHubIcon className="h-5 w-5" /> {check.repo_owner}/{check.repo_name}
            </p>
            <div className="mt-3 space-y-2 text-sm text-muted">
              <p className="flex items-center gap-2"><BranchIcon className="h-4 w-4" /> {check.branch}</p>
              <p className="flex items-center gap-2">
                <CommitIcon className="h-4 w-4" /> <span className="font-mono text-gray-300">{check.commit_id.slice(0, 7)}</span> {check.commit_message}
              </p>
            </div>
            <h2 className="mb-3 mt-6 font-medium text-white">Detection result</h2>
            <div className="flex items-center gap-2">
              <TypeBadge type={check.project_type} />
              {check.framework && <span className="text-sm text-gray-300">{check.framework}</span>}
              {check.supported && <span className="text-sm text-muted">· port {check.internal_port}</span>}
            </div>
            <p className={`mt-2 text-sm ${check.supported ? "text-emerald-300" : "text-amber-300"}`}>{check.message}</p>
            <p className="mt-2 text-xs text-muted">Files found: {check.files_found.join(", ") || "none"}</p>
            <button className="btn btn-primary mt-6 w-full" onClick={save} disabled={!check.supported || loading !== ""}>
              {loading === "save" ? <Spinner /> : <CheckIcon />} Save application
            </button>
          </div>
          <div className="card overflow-hidden xl:col-span-3">
            <div className="border-b border-line px-5 py-3 text-sm font-medium text-white">Generated Dockerfile.deployforge</div>
            <pre className="max-h-[480px] overflow-auto bg-black/40 p-5 font-mono text-xs leading-relaxed text-gray-300">
              {check.dockerfile || "# No Dockerfile: project type is not supported yet"}
            </pre>
          </div>
        </div>
      )}
    </>
  );
}
