"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "./ThemeProvider";
import { Sun, Moon, Menu, X, Sparkles, Activity } from "lucide-react";

interface NavLink {
  label: string;
  href: string;
}

const navLinks: NavLink[] = [
  { label: "Plan", href: "/" },
  { label: "Goals", href: "/goals" },
  { label: "Insights", href: "/insights" },
  { label: "Settings", href: "/settings" },
  { label: "Design System", href: "/design" },
];

export function Navbar() {
  const pathname = usePathname();
  const { resolvedTheme, toggleTheme } = useTheme();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-40 w-full h-12 apple-glass transition-colors">
      <div className="max-w-[1200px] h-full mx-auto px-4 sm:px-6 flex items-center justify-between">
        {/* Brand / Logo */}
        <Link
          href="/"
          className="flex items-center gap-2 group text-[14px] font-semibold tracking-tight text-[var(--text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] rounded-lg px-1.5 py-0.5"
        >
          <div className="w-5 h-5 rounded-md bg-[var(--text-primary)] text-[var(--bg-primary)] flex items-center justify-center transition-transform group-hover:scale-105">
            <Sparkles className="w-3 h-3 text-[var(--bg-primary)]" strokeWidth={1.5} />
          </div>
          <span>NeuroFlow</span>
        </Link>

        {/* Desktop Centered Links */}
        <div className="hidden md:flex items-center gap-7">
          {navLinks.map((link) => {
            const isActive =
              link.href === "/"
                ? pathname === "/"
                : pathname.startsWith(link.href);

            return (
              <Link
                key={link.href}
                href={link.href}
                className={`text-[12px] font-normal transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] rounded px-1.5 py-0.5 ${
                  isActive
                    ? "text-[var(--text-primary)] font-medium"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </div>

        {/* Right side: Theme toggle and mobile menu button */}
        <div className="flex items-center gap-2">
          {/* Theme Toggle Button */}
          <button
            onClick={toggleTheme}
            aria-label="Toggle light and dark mode"
            className="w-7 h-7 rounded-full flex items-center justify-center text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            {resolvedTheme === "dark" ? (
              <Sun className="w-4 h-4" strokeWidth={1.5} />
            ) : (
              <Moon className="w-4 h-4" strokeWidth={1.5} />
            )}
          </button>

          {/* Mobile Menu Hamburger */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Open mobile navigation menu"
            className="md:hidden w-7 h-7 rounded-full flex items-center justify-center text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            {mobileMenuOpen ? (
              <X className="w-4 h-4" strokeWidth={1.5} />
            ) : (
              <Menu className="w-4 h-4" strokeWidth={1.5} />
            )}
          </button>
        </div>
      </div>

      {/* Mobile Collapsible Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden apple-glass border-b border-[var(--border-hairline)] px-6 py-4 space-y-3 animate-fade-rise">
          {navLinks.map((link) => {
            const isActive =
              link.href === "/"
                ? pathname === "/"
                : pathname.startsWith(link.href);

            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`block text-[15px] py-1.5 font-medium transition-colors ${
                  isActive
                    ? "text-[var(--accent)]"
                    : "text-[var(--text-primary)] hover:text-[var(--accent)]"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </div>
      )}
    </nav>
  );
}
