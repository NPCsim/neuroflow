"use client";

import React from "react";
import { ChevronRight, Loader2 } from "lucide-react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "link";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: "left" | "right";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = "primary",
      size = "md",
      loading = false,
      icon,
      iconPosition = "left",
      className = "",
      disabled,
      ...props
    },
    ref
  ) => {
    // Size tokens
    const sizeClasses = {
      sm: "h-7 px-3.5 text-[12px] gap-1.5",
      md: "h-9 px-5 text-[14px] gap-2",
      lg: "h-11 px-6 text-[17px] gap-2.5",
    }[size];

    // Variant tokens
    const variantClasses = {
      primary:
        "bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white font-medium rounded-full shadow-[0_2px_8px_rgba(0,113,227,0.25)] dark:shadow-[0_2px_12px_rgba(41,151,255,0.25)] active:scale-[0.98]",
      secondary:
        "bg-[var(--bg-tertiary)] hover:bg-[var(--border-subtle)] text-[var(--text-primary)] font-medium rounded-full active:scale-[0.98]",
      outline:
        "border border-[var(--border-subtle)] hover:border-[var(--text-primary)] text-[var(--text-primary)] bg-transparent font-medium rounded-full active:scale-[0.98]",
      ghost:
        "hover:bg-[var(--bg-secondary)] text-[var(--text-primary)] font-medium rounded-full active:scale-[0.98]",
      link:
        "text-[var(--link)] hover:underline inline-flex items-center gap-1 font-normal p-0 h-auto rounded-none !shadow-none !bg-transparent",
    }[variant];

    if (variant === "link") {
      return (
        <button
          ref={ref}
          disabled={disabled || loading}
          className={`inline-flex items-center text-[var(--link)] group font-normal text-[14px] hover:opacity-85 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:opacity-40 disabled:cursor-not-allowed ${className}`}
          {...props}
        >
          {loading && <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" strokeWidth={1.5} />}
          {!loading && icon && iconPosition === "left" && <span className="mr-1">{icon}</span>}
          <span>{children}</span>
          {!loading && (icon ? iconPosition === "right" && <span className="ml-1">{icon}</span> : (
            <ChevronRight className="w-3.5 h-3.5 ml-0.5 transition-transform group-hover:translate-x-0.5" strokeWidth={1.5} />
          ))}
        </button>
      );
    }

    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={`inline-flex items-center justify-center transition-all duration-200 select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-primary)] disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100 ${sizeClasses} ${variantClasses} ${className}`}
        {...props}
      >
        {loading ? (
          <Loader2 className="w-4 h-4 animate-spin" strokeWidth={1.5} />
        ) : (
          <>
            {icon && iconPosition === "left" && <span className="shrink-0">{icon}</span>}
            <span>{children}</span>
            {icon && iconPosition === "right" && <span className="shrink-0">{icon}</span>}
          </>
        )}
      </button>
    );
  }
);

Button.displayName = "Button";
