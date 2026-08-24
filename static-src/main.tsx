import React from "react";
import { createRoot } from "react-dom/client";
import { TerminalDashboard } from "../app/components/TerminalDashboard";
import "../app/globals.css";
import "../app/readability.css";

const known = new Set(["allocation", "regime", "correlation", "markets", "etf-flows", "ai-chain", "calendar", "research", "workspace", "report"]);
const tail = window.location.pathname.split("/").filter(Boolean).at(-1) ?? "";
const section = known.has(tail) ? tail : "overview";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode><TerminalDashboard section={section} /></React.StrictMode>,
);

