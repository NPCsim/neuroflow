"use client";

import React from "react";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "neutral" | "blue" | "green" | "orange" | "purple" | "pink" | "teal";
  size?: "sm" | "md";
  dot?: boolean;
}

export function Badge({
  children,
  variant = "neutral",
  size = "md",
  dot = false,
  className = "",
  ...props
}: BadgeProps) {
  const sizeClasses = {
    sm: "h-5 px-2.5 text-[11px]",
    md: "h-6 px-3 text-[12px]",
  }[size];

  const variantStyles = {
    neutral: {
      bg: "bg-[var(--bg-tertiary)]",
      text: "text-[var(--text-secondary)]",
      dot: "bg-[var(--text-tertiary)]",
    },
    blue: {
      bg: "bg-[var(--cat-blue-bg)]",
      text: "text-[var(--cat-blue-text)]",
      dot: "bg-[var(--cat-blue-text)]",
    },
    green: {
      bg: "bg-[var(--cat-green-bg)]",
      text: "text-[var(--cat-green-text)]",
      dot: "bg-[var(--cat-green-text)]",
    },
    orange: {
      bg: "bg-[var(--cat-orange-bg)]",
      text: "text-[var(--cat-orange-text)]",
      dot: "bg-[var(--cat-orange-text)]",
    },
    purple: {
      bg: "bg-[var(--cat-purple-bg)]",
      text: "text-[var(--cat-purple-text)]",
      dot: "bg-[var(--cat-purple-text)]",
    },
    pink: {
      bg: "bg-[var(--cat-pink-bg)]",
      text: "text-[var(--cat-pink-text)]",
      dot: "bg-[var(--cat-pink-text)]",
    },
    teal: {
      bg: "bg-[var(--cat-teal-bg)]",
      text: "text-[var(--cat-teal-text)]",
      dot: "bg-[var(--cat-teal-text)]",
    },
  }[variant];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium tracking-tight select-none ${sizeClasses} ${variantStyles.bg} ${variantStyles.text} ${className}`}
      {...props}
    >
      {dot && (
        <span
          className={`w-1.5 h-1.5 rounded-full shrink-0 ${variantStyles.dot}`}
          aria-hidden="true"
        />
      )}
      <span>{children}</span>
    </span>
  );
}
