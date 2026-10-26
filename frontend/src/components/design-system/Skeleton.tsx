"use client";

import React from "react";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "text" | "rectangular" | "circular" | "pill";
  width?: string | number;
  height?: string | number;
}

export function Skeleton({
  variant = "rectangular",
  width,
  height,
  className = "",
  style,
  ...props
}: SkeletonProps) {
  const variantRadius = {
    text: "rounded-md",
    rectangular: "rounded-xl",
    circular: "rounded-full aspect-square",
    pill: "rounded-full",
  }[variant];

  const defaultHeight = {
    text: "h-4",
    rectangular: "h-24",
    circular: "h-10 w-10",
    pill: "h-7",
  }[variant];

  return (
    <div
      className={`animate-pulse bg-[var(--bg-tertiary)]/70 ${variantRadius} ${
        height ? "" : defaultHeight
      } ${className}`}
      style={{
        width: typeof width === "number" ? `${width}px` : width,
        height: typeof height === "number" ? `${height}px` : height,
        ...style,
      }}
      aria-hidden="true"
      {...props}
    />
  );
}
