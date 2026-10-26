"use client";

import React, { useEffect } from "react";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";

export interface ToastProps {
  id?: string;
  message: string;
  type?: "success" | "error" | "info";
  isOpen: boolean;
  onClose: () => void;
  duration?: number;
}

export function Toast({
  message,
  type = "success",
  isOpen,
  onClose,
  duration = 3000,
}: ToastProps) {
  useEffect(() => {
    if (!isOpen) return;
    const timer = setTimeout(() => {
      onClose();
    }, duration);
    return () => clearTimeout(timer);
  }, [isOpen, duration, onClose]);

  if (!isOpen) return null;

  const icons = {
    success: <CheckCircle2 className="w-4 h-4 text-emerald-500" strokeWidth={1.5} />,
    error: <AlertCircle className="w-4 h-4 text-rose-500" strokeWidth={1.5} />,
    info: <Info className="w-4 h-4 text-[var(--accent)]" strokeWidth={1.5} />,
  }[type];

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 animate-fade-rise pointer-events-auto">
      <div className="h-11 px-4 rounded-full bg-[var(--bg-elevated)]/90 backdrop-blur-md border border-[var(--border-hairline)] shadow-[var(--shadow-elevated)] flex items-center gap-3 text-[13px] font-medium text-[var(--text-primary)]">
        {icons}
        <span>{message}</span>
        <button
          onClick={onClose}
          aria-label="Close notification"
          className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors p-0.5 ml-1"
        >
          <X className="w-3.5 h-3.5" strokeWidth={1.5} />
        </button>
      </div>
    </div>
  );
}
