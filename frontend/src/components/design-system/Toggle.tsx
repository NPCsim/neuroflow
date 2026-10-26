"use client";

import React from "react";

export interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
  color?: "green" | "blue";
  id?: string;
}

export function Toggle({
  checked,
  onChange,
  label,
  description,
  disabled = false,
  color = "green",
  id,
}: ToggleProps) {
  const switchId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

  const activeColorClass =
    color === "green" ? "bg-[#34c759] dark:bg-[#30d158]" : "bg-[var(--accent)]";

  return (
    <div className="flex items-center justify-between gap-4 select-none">
      {(label || description) && (
        <label htmlFor={switchId} className="cursor-pointer space-y-0.5">
          {label && (
            <span className="block text-[15px] font-medium text-[var(--text-primary)]">
              {label}
            </span>
          )}
          {description && (
            <span className="block text-[13px] text-[var(--text-secondary)]">
              {description}
            </span>
          )}
        </label>
      )}

      <button
        id={switchId}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={`relative inline-flex h-[30px] w-[50px] shrink-0 cursor-pointer rounded-full p-[2px] transition-colors duration-200 ease-in-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-primary)] disabled:opacity-40 disabled:cursor-not-allowed ${
          checked ? activeColorClass : "bg-[#e5e5ea] dark:bg-[#39393d]"
        }`}
      >
        <span
          className={`pointer-events-none inline-block h-[26px] w-[26px] rounded-full bg-white shadow-[0_2px_6px_rgba(0,0,0,0.2)] transform transition-transform duration-200 ease-in-out ${
            checked ? "translate-x-[20px]" : "translate-x-0"
          }`}
        />
      </button>
    </div>
  );
}
