import React from "react";
import { createRoot } from "react-dom/client";
import { TerminalDashboard } from "../app/components/TerminalDashboard";
import "../app/globals.css";
import "../app/readability.css";

const known = new Set(["allocation", "regime", "correlation", "markets", "etf-flows", "ai-chain", "calendar", "research"]);
const parts = window.location.pathname.split("/").filter(Boolean).filter((part) => part !== "asset-allocation-dashboard");
const section = known.has(parts[0] ?? "") ? parts[0] : "overview";
const detail = section === "allocation" ? parts[1] : undefined;

createRoot(document.getElementById("root")!).render(
  <React.StrictMode><TerminalDashboard section={section} detail={detail} /></React.StrictMode>,
);

