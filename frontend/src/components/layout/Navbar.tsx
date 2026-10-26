"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "@/components/design-system/ThemeProvider";
import { BackendStatusBadge } from "./BackendStatusBadge";
import { Sun, Moon, Menu, X, Sparkles, CalendarDays, Target, BarChart3, Settings } from "lucide-react";

const navLinks = [
  { name: "Plan", href: "/", icon: CalendarDays },
  { name: "Goals", href: "/goals", icon: Target },
  { name: "Insights", href: "/insights", icon: BarChart3 },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Navbar() {
  const pathname = usePathname();
  const { resolvedTheme, toggleTheme } = useTheme();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <>
      <header className="fixed top-0 left-0 right-0 z-50 h-12 apple-glass border-b border-[var(--border-hairline)] transition-colors duration-200">
        <div className="max-w-[1200px] h-full mx-auto px-4 sm:px-6 flex items-center justify-between">
          {/* Brand Logo */}
          <Link
            href="/"
            className="flex items-center gap-2 group transition-opacity hover:opacity-85"
            onClick={() => setMobileMenuOpen(false)}
          >
            <div className="w-6 h-6 rounded-md bg-[var(--accent)] flex items-center justify-center text-white shadow-sm">
              <Sparkles className="w-3.5 h-3.5" />
            </div>
            <span className="font-semibold text-[15px] tracking-[-0.015em] text-[var(--text-primary)]">
              NeuroFlow
            </span>
          </Link>

          {/* Desktop Nav Links (Centered Horizontal Strip) */}
          <nav className="hidden md:flex items-center gap-8 text-[12px] font-normal tracking-normal text-[var(--text-secondary)]">
            {navLinks.map((item) => {
              const isActive =
                item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`transition-colors duration-150 relative py-1 ${
                    isActive
                      ? "text-[var(--text-primary)] font-medium"
                      : "hover:text-[var(--text-primary)]"
                  }`}
                >
                  {item.name}
                  {isActive && (
                    <span className="absolute bottom-0 left-0 right-0 h-[2px] rounded-full bg-[var(--accent)]" />
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Right Controls */}
          <div className="flex items-center gap-3">
            {/* Live Backend Connection Indicator (Compact) */}
            <div className="hidden sm:block scale-90 origin-right">
              <BackendStatusBadge />
            </div>

            {/* Light / Dark Mode Toggle */}
            <button
              onClick={toggleTheme}
              aria-label="Toggle light and dark mode"
              className="p-1.5 rounded-full hover:bg-[var(--fill-tertiary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-all cursor-pointer border border-[var(--border-hairline)]"
            >
              {resolvedTheme === "dark" ? (
                <Sun className="w-4 h-4 text-amber-300 transition-transform hover:rotate-45" />
              ) : (
                <Moon className="w-4 h-4 text-slate-700 transition-transform hover:-rotate-12" />
              )}
            </button>

            {/* Mobile Hamburger Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Open mobile navigation menu"
              className="md:hidden p-1.5 rounded-md text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden fixed inset-0 top-12 z-40 bg-[var(--bg-primary)]/95 backdrop-blur-xl transition-all duration-200 p-6 flex flex-col justify-between">
          <nav className="space-y-4 pt-4">
            {navLinks.map((item) => {
              const isActive =
                item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              const Icon = item.icon;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-3 text-lg font-medium px-4 py-3 rounded-2xl transition-all ${
                    isActive
                      ? "bg-[var(--accent)] text-white shadow-sm"
                      : "text-[var(--text-primary)] hover:bg-[var(--fill-tertiary)]"
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>

          <div className="pt-6 border-t border-[var(--border-hairline)] space-y-4">
            <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
              <span>Appearance</span>
              <button
                onClick={toggleTheme}
                className="px-3 py-1.5 rounded-full border border-[var(--border-hairline)] text-xs flex items-center gap-1.5 text-[var(--text-primary)] font-medium"
              >
                {resolvedTheme === "dark" ? (
                  <>
                    <Sun className="w-3.5 h-3.5 text-amber-300" />
                    <span>Dark Mode</span>
                  </>
                ) : (
                  <>
                    <Moon className="w-3.5 h-3.5 text-slate-700" />
                    <span>Light Mode</span>
                  </>
                )}
              </button>
            </div>
            <div className="flex justify-center">
              <BackendStatusBadge />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
