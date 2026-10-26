"use client";

import { usePathname } from "next/navigation";
import { BackendStatusBadge } from "./BackendStatusBadge";
import { Sparkles, Clock, Calendar } from "lucide-react";
import { useEffect, useState } from "react";

const pageTitles: Record<string, { title: string; subtitle: string }> = {
  "/": {
    title: "Daily Plan & Schedule",
    subtitle: "Deterministic timeline mapped around fixed events and working hours",
  },
  "/goals": {
    title: "Goals & Decomposed Tasks",
    subtitle: "High-level objectives broken down into actionable, prioritized work",
  },
  "/insights": {
    title: "Productivity & Cognitive Insights",
    subtitle: "Workload distribution, cognitive load balance, and schedule metrics",
  },
  "/settings": {
    title: "Settings & Scheduling Constraints",
    subtitle: "Timezone, working hours, minimum chunk size, and rest buffers",
  },
};

export function Header() {
  const pathname = usePathname();
  const [currentTime, setCurrentTime] = useState<string>("");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(
        now.toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: true,
        })
      );
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  const meta = pageTitles[pathname] || {
    title: "NeuroFlow",
    subtitle: "Autonomous AI Productivity Agent",
  };

  return (
    <header className="h-16 fixed top-0 right-0 left-64 z-30 flex items-center justify-between px-8 border-b border-white/10 bg-[#090d16]/80 backdrop-blur-md">
      <div>
        <h1 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
          {meta.title}
        </h1>
        <p className="text-xs text-slate-400 font-normal">{meta.subtitle}</p>
      </div>

      <div className="flex items-center gap-4">
        {/* Live Clock */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/10 text-xs text-slate-300">
          <Clock className="w-3.5 h-3.5 text-cyan-400" />
          <span className="font-mono">{currentTime || "..."}</span>
          <span className="text-[10px] text-slate-500 uppercase">Local</span>
        </div>

        {/* Backend Connected Badge */}
        <BackendStatusBadge />
      </div>
    </header>
  );
}
