// Decides which page to show for the current URL.

import { useEffect } from "react";
import { getToken } from "./api";
import Layout from "./components/Layout";
import BuildLogs from "./pages/BuildLogs";
import ConnectRepository from "./pages/ConnectRepository";
import CreateDeployment from "./pages/CreateDeployment";
import Dashboard from "./pages/Dashboard";
import DeploymentHistory from "./pages/DeploymentHistory";
import Login from "./pages/Login";
import Monitoring from "./pages/Monitoring";
import Projects from "./pages/Projects";
import Settings from "./pages/Settings";
import { navigate, useRoute } from "./router";

export default function App() {
  const { path, query } = useRoute();
  const loggedIn = Boolean(getToken());

  // Send visitors who are not logged in to the login page
  useEffect(() => {
    if (!loggedIn && path !== "/login") navigate("/login");
  }, [loggedIn, path]);

  if (path === "/login" || !loggedIn) return <Login />;

  let page;
  if (path === "/") page = <Dashboard />;
  else if (path === "/projects") page = <Projects />;
  else if (path === "/connect") page = <ConnectRepository />;
  else if (path === "/deploy") page = <CreateDeployment preselectedId={Number(query.get("app")) || null} />;
  else if (path.startsWith("/logs")) page = <BuildLogs deploymentId={Number(path.split("/")[2]) || null} />;
  else if (path === "/history") page = <DeploymentHistory preselectedId={Number(query.get("app")) || null} />;
  else if (path === "/monitoring") page = <Monitoring />;
  else if (path === "/settings") page = <Settings />;
  else
    page = (
      <div className="py-20 text-center">
        <p className="text-lg text-white">Page not found</p>
        <button className="btn btn-secondary mt-4" onClick={() => navigate("/")}>
          Go to dashboard
        </button>
      </div>
    );

  return <Layout path={path}>{page}</Layout>;
}
