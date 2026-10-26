"use client";

import React from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
  error?: string;
  icon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, helperText, error, icon, className = "", id, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

    return (
      <div className="w-full space-y-1.5 text-left">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-[13px] font-medium text-[var(--text-secondary)] tracking-tight"
          >
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          {icon && (
            <span className="absolute left-3.5 text-[var(--text-secondary)] pointer-events-none shrink-0 flex items-center">
              {icon}
            </span>
          )}
          <input
            id={inputId}
            ref={ref}
            className={`w-full h-11 px-3.5 ${
              icon ? "pl-10" : "pl-3.5"
            } rounded-xl bg-[var(--fill-input)] text-[var(--text-primary)] text-[15px] placeholder:text-[var(--text-tertiary)] border border-transparent focus:border-[var(--accent)] focus:bg-[var(--bg-elevated)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed ${
              error ? "!border-rose-500 !ring-rose-500/20" : ""
            } ${className}`}
            {...props}
          />
        </div>
        {error && <p className="text-[12px] text-rose-500 font-medium pl-1">{error}</p>}
        {!error && helperText && (
          <p className="text-[12px] text-[var(--text-secondary)] pl-1">{helperText}</p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
