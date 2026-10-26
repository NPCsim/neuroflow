"use client";

import React from "react";

export interface TabOption {
  id: string;
  label: string;
  icon?: React.ReactNode;
}

export interface TabsProps {
  options: TabOption[];
  activeId: string;
  onChange: (id: string) => void;
  size?: "sm" | "md";
  className?: string;
}

export function Tabs({
  options,
  activeId,
  onChange,
  size = "md",
  className = "",
}: TabsProps) {
  const sizeClasses = {
    sm: "h-8 p-1 text-[12px]",
    md: "h-10 p-1 text-[13px]",
  }[size];

  return (
    <div
      role="tablist"
      className={`inline-flex items-center rounded-full bg-[var(--bg-tertiary)] border border-[var(--border-hairline)] select-none ${sizeClasses} ${className}`}
    >
      {options.map((option) => {
        const isActive = option.id === activeId;
        return (
          <button
            key={option.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(option.id)}
            className={`relative flex items-center justify-center gap-1.5 px-4 h-full rounded-full font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
              isActive
                ? "bg-white text-[#1d1d1f] shadow-[0_2px_8px_rgba(0,0,0,0.12)] dark:bg-[#636366] dark:text-[#f5f5f7]"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            {option.icon && <span className="shrink-0">{option.icon}</span>}
            <span>{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}
