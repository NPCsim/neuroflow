"use client";

import React, { useState } from "react";
import {
  Sparkles,
  RefreshCw,
  Zap,
  TrendingUp,
  AlertCircle,
  Lightbulb,
  CheckCircle2,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";
import { RecommendationItem } from "./types";

interface AIRecommendationsPanelProps {
  recommendations: RecommendationItem[];
  isCached?: boolean;
  generatedAt?: string;
  isLoading?: boolean;
  onRefresh?: (force: boolean) => void;
}

export function AIRecommendationsPanel({
  recommendations,
  isCached = false,
  generatedAt,
  isLoading = false,
  onRefresh,
}: AIRecommendationsPanelProps) {
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    if (onRefresh) {
      setRefreshing(true);
      try {
        await onRefresh(true);
      } finally {
        setRefreshing(false);
      }
    }
  };

  const getImpactBadge = (impact: string) => {
    const imp = impact.toLowerCase();
    if (imp === "high") {
      return (
        <span className="text-xs px-2.5 py-0.5 rounded-full pastel-pink font-medium">
          High impact
        </span>
      );
    }
    if (imp === "medium") {
      return (
        <span className="text-xs px-2.5 py-0.5 rounded-full pastel-orange font-medium">
          Medium impact
        </span>
      );
    }
    return (
      <span className="text-xs px-2.5 py-0.5 rounded-full pastel-blue font-medium">
        Optimization
      </span>
    );
  };

  const getCategoryBadge = (category: string) => {
    return (
      <span className="text-xs uppercase tracking-wider px-2.5 py-0.5 rounded-md bg-[var(--bg-secondary)] text-[var(--text-secondary)] font-medium">
        {category}
      </span>
    );
  };

  const formatGeneratedAt = (isoString?: string) => {
    if (!isoString) return "Recently updated";
    try {
      const dt = new Date(isoString);
      return dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return "Today";
    }
  };

  return (
    <div className="apple-card p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-[var(--accent)]/10 text-[var(--accent)] flex items-center justify-center">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-[var(--text-primary)] tracking-tight">
                AI recommendations
              </h3>
              {isCached && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--bg-secondary)] text-[var(--text-secondary)]">
                  Cached
                </span>
              )}
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Capacity optimizations grounded in your completion history
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-[var(--text-secondary)]">
            Updated {formatGeneratedAt(generatedAt)}
          </span>
          <button
            onClick={handleRefresh}
            disabled={isLoading || refreshing}
            className="px-3.5 py-1.5 rounded-full border border-[var(--border-subtle)] bg-[var(--bg-elevated)] hover:bg-[var(--bg-secondary)] text-xs text-[var(--text-primary)] transition-all flex items-center gap-1.5 shadow-sm disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading || refreshing ? "animate-spin" : ""}`} />
            <span>Regenerate</span>
          </button>
        </div>
      </div>

      {/* Recommendations List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {recommendations.length > 0 ? (
          recommendations.map((rec) => (
            <div
              key={rec.id}
              className="p-5 rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border-subtle)] space-y-3 transition-all hover:shadow-sm"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  {getImpactBadge(rec.impact)}
                  {getCategoryBadge(rec.category)}
                </div>
              </div>

              <div>
                <h4 className="text-sm font-semibold text-[var(--text-primary)] tracking-tight">
                  {rec.title}
                </h4>
                <p className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">
                  {rec.description}
                </p>
              </div>

              {rec.actionable_step && (
                <div className="pt-2 border-t border-[var(--border-subtle)] flex items-center gap-2 text-xs text-[var(--accent)] font-medium">
                  <ArrowRight className="w-3.5 h-3.5" />
                  <span>{rec.actionable_step}</span>
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="col-span-2 p-8 text-center text-xs text-[var(--text-secondary)]">
            No recommendations generated yet. Complete more focus blocks to receive personalized insights.
          </div>
        )}
      </div>
    </div>
  );
}
