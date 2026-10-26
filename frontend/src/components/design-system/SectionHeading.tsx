"use client";

import React from "react";

export interface SectionHeadingProps {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  align?: "center" | "left";
  hero?: boolean;
  className?: string;
}

export function SectionHeading({
  eyebrow,
  title,
  subtitle,
  align = "center",
  hero = false,
  className = "",
}: SectionHeadingProps) {
  const alignmentClass = align === "center" ? "text-center mx-auto" : "text-left";

  return (
    <div className={`space-y-3 ${alignmentClass} ${className}`}>
      {eyebrow && (
        <p className="text-[12px] sm:text-[13px] font-semibold uppercase tracking-wider text-[var(--accent)] select-none">
          {eyebrow}
        </p>
      )}

      {hero ? (
        <h1 className="text-[40px] sm:text-[56px] lg:text-[72px] font-semibold tracking-[-0.03em] leading-[1.05] text-[var(--text-primary)] max-w-4xl">
          {title}
        </h1>
      ) : (
        <h2 className="text-[28px] sm:text-[36px] lg:text-[44px] font-semibold tracking-[-0.02em] leading-[1.15] text-[var(--text-primary)] max-w-3xl">
          {title}
        </h2>
      )}

      {subtitle && (
        <p className="text-[16px] sm:text-[17px] lg:text-[19px] leading-[1.47] text-[var(--text-secondary)] font-normal max-w-2xl">
          {subtitle}
        </p>
      )}
    </div>
  );
}
