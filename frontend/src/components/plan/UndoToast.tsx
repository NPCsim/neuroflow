"use client";

import React, { useEffect } from "react";
import { CheckCircle2, RotateCcw, X, Loader2 } from "lucide-react";

interface UndoToastProps {
  isOpen: boolean;
  message: string;
  onClose: () => void;
  onUndo: () => Promise<void>;
  isUndoing?: boolean;
  duration?: number;
}

export function UndoToast({
  isOpen,
  message,
  onClose,
  onUndo,
  isUndoing = false,
  duration = 8000,
}: UndoToastProps) {
  useEffect(() => {
    if (!isOpen) return;
    const timer = setTimeout(() => {
      onClose();
    }, duration);
    return () => clearTimeout(timer);
  }, [isOpen, duration, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed bottom-24 left-1/2 -translate-x-1/2 z-50 animate-fade-rise pointer-events-auto">
      <div className="px-5 py-2.5 rounded-full bg-[#0d1322]/95 border border-indigo-500/40 shadow-[0_12px_40px_rgba(0,0,0,0.7)] backdrop-blur-xl flex items-center gap-4 text-xs font-medium text-white">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span className="truncate max-w-xs sm:max-w-md">{message}</span>
        </div>

        <button
          onClick={onUndo}
          disabled={isUndoing}
          aria-label="Undo applied changes"
          className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/25 hover:bg-indigo-500/40 text-cyan-300 hover:text-white border border-indigo-400/40 font-semibold text-xs transition-all active:scale-95 disabled:opacity-40 cursor-pointer"
        >
          {isUndoing ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <RotateCcw className="w-3.5 h-3.5" />
          )}
          <span>Undo</span>
        </button>

        <button
          onClick={onClose}
          aria-label="Close notification"
          className="text-slate-400 hover:text-white transition-colors p-0.5 ml-1"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
