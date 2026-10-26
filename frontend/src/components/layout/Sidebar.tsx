"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  CalendarDays,
  Target,
  BarChart3,
  Settings,
  Sparkles,
  Zap,
} from "lucide-react";

interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
}

const navItems: NavItem[] = [
  { name: "Plan", href: "/", icon: CalendarDays },
  { name: "Goals", href: "/goals", icon: Target, badge: "3" },
  { name: "Insights", href: "/insights", icon: BarChart3 },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 h-screen fixed left-0 top-0 z-40 flex flex-col justify-between glass-panel border-r border-white/10 bg-[#090d16]/90 p-4">
      <div className="space-y-6">
        {/* Brand / Logo */}
        <Link href="/" className="flex items-center gap-3 px-2 py-1 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 p-0.5 shadow-lg shadow-indigo-500/25 flex items-center justify-center transition-transform group-hover:scale-105">
            <div className="w-full h-full bg-[#090d16] rounded-[10px] flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-cyan-400 animate-pulse" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
                NeuroFlow
              </span>
              <span className="text-[10px] font-semibold tracking-wider uppercase px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                AI
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">Deterministic Agent</p>
          </div>
        </Link>

        {/* Navigation */}
        <nav className="space-y-1">
          <p className="px-3 text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-2">
            Navigation
          </p>
          {navItems.map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all group ${
                  isActive
                    ? "bg-gradient-to-r from-indigo-600/30 to-cyan-500/10 text-white border border-indigo-500/30 shadow-[0_0_20px_-5px_rgba(99,102,241,0.3)]"
                    : "text-slate-400 hover:text-white hover:bg-white/[0.04] border border-transparent"
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={`w-4 h-4 transition-colors ${
                      isActive
                        ? "text-cyan-400"
                        : "text-slate-400 group-hover:text-slate-200"
                    }`}
                  />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[11px] px-2 py-0.5 rounded-full font-semibold ${
                      isActive
                        ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                        : "bg-white/5 text-slate-400 group-hover:text-slate-300"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer Info / Hackathon Demo card */}
      <div className="space-y-3">
        <div className="p-3 rounded-xl bg-gradient-to-br from-indigo-950/40 to-slate-900/60 border border-indigo-500/20 shadow-inner">
          <div className="flex items-center gap-2 mb-1.5">
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-xs font-semibold text-slate-200">
              Deterministic Mode
            </span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Strict capacity limits enforced. LLM proposes; solver places.
          </p>
        </div>

        <div className="flex items-center gap-3 px-2 pt-2 border-t border-white/5">
          <div className="w-8 h-8 rounded-full bg-indigo-500/20 border border-indigo-400/30 flex items-center justify-center font-bold text-xs text-indigo-300">
            NF
          </div>
          <div className="overflow-hidden">
            <p className="text-xs font-medium text-slate-200 truncate">Demo User</p>
            <p className="text-[10px] text-slate-400 truncate">America/New_York (UTC-4)</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
