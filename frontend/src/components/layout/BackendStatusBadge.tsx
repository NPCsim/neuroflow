"use client";

import { useEffect, useState } from "react";
import { Activity, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";
import { API_BASE_URL } from "@/lib/api";

interface HealthData {
  status: string;
  app: string;
  version: string;
  timestamp: string;
  database: string;
}

export function BackendStatusBadge() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [latency, setLatency] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const checkHealth = async () => {
    setLoading(true);
    const start = performance.now();
    try {
      const res = await fetch(`${API_BASE_URL}/health`, {
        cache: "no-store",
      });
      const end = performance.now();
      setLatency(Math.round(end - start));

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data: HealthData = await res.json();
      setHealth(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to connect");
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 10000); // Check every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const isConnected = !!health && health.status === "ok";

  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
        isConnected
          ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400 shadow-[0_0_15px_-3px_rgba(16,185,129,0.3)]"
          : "bg-rose-500/10 border-rose-500/30 text-rose-400 shadow-[0_0_15px_-3px_rgba(244,63,94,0.3)]"
      }`}
      title={
        isConnected
          ? `Connected to ${health?.app} (DB: ${health?.database}) • ${latency}ms`
          : `Backend Unreachable: ${error}`
      }
    >
      <span className="relative flex h-2 w-2">
        {isConnected ? (
          <>
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </>
        ) : (
          <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
        )}
      </span>

      <span className="font-semibold tracking-wide">
        {isConnected ? "Backend Connected" : "Backend Offline"}
      </span>

      {isConnected && latency !== null && (
        <span className="text-[10px] text-emerald-300/70 font-mono">
          {latency}ms
        </span>
      )}

      <button
        onClick={checkHealth}
        disabled={loading}
        className="text-slate-400 hover:text-white transition-colors p-0.5"
        aria-label="Refresh status"
      >
        <RefreshCw
          className={`w-3 h-3 ${loading ? "animate-spin text-slate-300" : ""}`}
        />
      </button>
    </div>
  );
}
