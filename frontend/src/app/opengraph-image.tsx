import { ImageResponse } from "next/og";

export const alt = "NeuroFlow - Autonomous AI Productivity & Deterministic Scheduler";
export const size = {
  width: 1200,
  height: 630,
};
export const contentType = "image/png";

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#090d16",
          backgroundImage: "radial-gradient(circle at 50% 30%, #1e1b4b 0%, #090d16 80%)",
          fontFamily: "sans-serif",
          padding: "60px",
          color: "white",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "16px",
            marginBottom: "24px",
          }}
        >
          <div
            style={{
              width: "56px",
              height: "56px",
              borderRadius: "16px",
              background: "linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #06b6d4 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 40px rgba(99, 102, 241, 0.4)",
              fontSize: "28px",
            }}
          >
            ⚡
          </div>
          <span
            style={{
              fontSize: "36px",
              fontWeight: 800,
              letterSpacing: "-0.03em",
              color: "#ffffff",
            }}
          >
            NeuroFlow
          </span>
        </div>
        <div
          style={{
            fontSize: "52px",
            fontWeight: 800,
            textAlign: "center",
            lineHeight: 1.15,
            letterSpacing: "-0.03em",
            maxWidth: "960px",
            marginBottom: "20px",
          }}
        >
          Autonomous AI Productivity &amp; Deterministic Scheduler
        </div>
        <div
          style={{
            fontSize: "22px",
            color: "#94a3b8",
            textAlign: "center",
            maxWidth: "820px",
            lineHeight: 1.4,
          }}
        >
          Goal decomposition, automatic conflict resolution, staged plan diffs, and instant rollbacks.
        </div>
        <div
          style={{
            display: "flex",
            gap: "20px",
            marginTop: "36px",
          }}
        >
          <div
            style={{
              padding: "10px 22px",
              borderRadius: "9999px",
              backgroundColor: "rgba(99, 102, 241, 0.15)",
              border: "1px solid rgba(99, 102, 241, 0.3)",
              color: "#a5b4fc",
              fontSize: "16px",
              fontWeight: 600,
            }}
          >
            Deterministic Engine
          </div>
          <div
            style={{
              padding: "10px 22px",
              borderRadius: "9999px",
              backgroundColor: "rgba(6, 182, 212, 0.15)",
              border: "1px solid rgba(6, 182, 212, 0.3)",
              color: "#67e8f9",
              fontSize: "16px",
              fontWeight: 600,
            }}
          >
            Zero Direct DB Mutations
          </div>
          <div
            style={{
              padding: "10px 22px",
              borderRadius: "9999px",
              backgroundColor: "rgba(168, 85, 247, 0.15)",
              border: "1px solid rgba(168, 85, 247, 0.3)",
              color: "#d8b4fe",
              fontSize: "16px",
              fontWeight: 600,
            }}
          >
            Instant Undo &amp; Diff
          </div>
        </div>
      </div>
    ),
    {
      ...size,
    }
  );
}
