import { useState, type FormEvent } from "react";
import { api, setToken } from "../api";
import { Logo } from "../components/Layout";
import { ErrorBox, Spinner } from "../components/ui";
import { navigate } from "../router";

export default function Login() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const result = await api.login(username, password);
      setToken(result.token);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-full items-center justify-center overflow-hidden px-4 py-12">
      {/* soft blue/violet glow in the background */}
      <div className="pointer-events-none absolute -top-40 left-1/2 h-[480px] w-[720px] -translate-x-1/2 rounded-full bg-gradient-to-r from-brand-blue/20 to-brand-violet/20 blur-3xl" />

      <div className="relative w-full max-w-sm">
        <div className="mb-8 flex justify-center">
          <Logo />
        </div>
        <form onSubmit={submit} className="card p-6 shadow-2xl shadow-black/40">
          <h1 className="text-lg font-semibold text-white">Sign in</h1>
          <p className="mb-5 mt-1 text-sm text-muted">Deploy GitHub projects to Docker in one click.</p>
          <ErrorBox message={error} />
          <label className="label" htmlFor="username">Username</label>
          <input id="username" className="input mb-4" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
          <label className="label" htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            className="input mb-6"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            autoFocus
          />
          <button type="submit" className="btn btn-primary w-full" disabled={loading || !password}>
            {loading && <Spinner />} Sign in
          </button>
        </form>
        <p className="mt-4 text-center text-xs text-muted">
          Default login is <span className="font-mono text-gray-300">admin / admin123</span>. Change it in the .env file.
        </p>
      </div>
    </div>
  );
}
