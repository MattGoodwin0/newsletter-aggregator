import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import FeedValidator from "./FeedValidator.jsx";
import About from "./About.jsx";
import "./index.css";

function getPage() {
  const hash = window.location.hash;
  if (hash === "#validator") return "validator";
  if (hash === "#about") return "about";
  return "home";
}

function Router() {
  const [page, setPage] = React.useState(getPage);

  React.useEffect(() => {
    const handler = () => setPage(getPage());
    window.addEventListener("hashchange", handler);
    return () => window.removeEventListener("hashchange", handler);
  }, []);

  if (page === "validator") return <FeedValidator />;
  if (page === "about") return <About />;
  return <App />;
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Router />
  </React.StrictMode>,
);
