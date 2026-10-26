"use client";

import React from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverable?: boolean;
  padding?: "sm" | "md" | "lg" | "none";
  eyebrow?: string;
  title?: string;
  subtitle?: string;
}

export function Card({
  children,
  hoverable = false,
  padding = "md",
  eyebrow,
  title,
  subtitle,
  className = "",
  ...props
}: CardProps) {
  const paddingClasses = {
    none: "p-0",
    sm: "p-4 sm:p-5",
    md: "p-6 sm:p-8",
    lg: "p-8 sm:p-10",
  }[padding];

  return (
    <div
      className={`apple-card ${hoverable ? "apple-card-hover cursor-pointer" : ""} ${paddingClasses} ${className}`}
      {...props}
    >
      {(eyebrow || title || subtitle) && (
        <div className="mb-4 space-y-1">
          {eyebrow && (
            <p className="text-[12px] font-semibold uppercase tracking-wider text-[var(--accent)]">
              {eyebrow}
            </p>
          )}
          {title && (
            <h3 className="text-[21px] font-semibold text-[var(--text-primary)] tracking-tight">
              {title}
            </h3>
          )}
          {subtitle && (
            <p className="text-[15px] text-[var(--text-secondary)] leading-relaxed">
              {subtitle}
            </p>
          )}
        </div>
      )}
      {children}
    </div>
  );
}
