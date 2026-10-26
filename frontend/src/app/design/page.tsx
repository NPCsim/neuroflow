"use client";

import React, { useState } from "react";
import {
  Navbar,
  Button,
  Card,
  Input,
  Badge,
  Toggle,
  Modal,
  Toast,
  Skeleton,
  Tabs,
  SectionHeading,
  useTheme,
} from "@/components/design-system";
import {
  Sparkles,
  Search,
  Check,
  Calendar,
  Layers,
  ArrowRight,
  Sun,
  Moon,
  Laptop,
  Clock,
  ShieldCheck,
  Compass,
} from "lucide-react";

export default function DesignSystemPage() {
  const { theme, resolvedTheme, setTheme } = useTheme();

  // Interactive states for components
  const [toggle1, setToggle1] = useState(true);
  const [toggle2, setToggle2] = useState(false);
  const [activeTab, setActiveTab] = useState("daily");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isToastOpen, setIsToastOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");

  const tabOptions = [
    { id: "daily", label: "Daily" },
    { id: "weekly", label: "Weekly" },
    { id: "monthly", label: "Monthly" },
  ];

  const themeOptions = [
    { id: "light", label: "Light", icon: <Sun className="w-3.5 h-3.5" strokeWidth={1.5} /> },
    { id: "dark", label: "Dark", icon: <Moon className="w-3.5 h-3.5" strokeWidth={1.5} /> },
    { id: "system", label: "System", icon: <Laptop className="w-3.5 h-3.5" strokeWidth={1.5} /> },
  ];

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] transition-colors duration-200">
      <Navbar />

      {/* Floating Theme Control Pill */}
      <div className="sticky top-14 z-30 flex justify-center py-3 px-4">
        <div className="apple-glass rounded-full px-4 py-1.5 shadow-[var(--shadow-card)] flex items-center gap-3 border border-[var(--border-hairline)]">
          <span className="text-[12px] font-medium text-[var(--text-secondary)]">Theme:</span>
          <Tabs
            size="sm"
            options={themeOptions}
            activeId={theme}
            onChange={(id) => setTheme(id as any)}
          />
          <Badge variant="blue" size="sm">
            {resolvedTheme === "dark" ? "Dark Active" : "Light Active"}
          </Badge>
        </div>
      </div>

      {/* 1. Hero Section */}
      <section className="py-20 sm:py-28 px-6 max-w-[980px] mx-auto text-center space-y-6 animate-fade-rise">
        <SectionHeading
          hero
          eyebrow="Design System"
          title="Clean. Minimal. Spacious."
          subtitle="A refined design language engineered for cognitive clarity, generous whitespace, and restrained typography."
        />

        <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
          <Button size="lg" onClick={() => setIsToastOpen(true)}>
            Explore components
          </Button>
          <Button
            variant="link"
            size="lg"
            onClick={() => {
              document.getElementById("typography")?.scrollIntoView({ behavior: "smooth" });
            }}
          >
            View typography guidelines
          </Button>
        </div>
      </section>

      {/* 2. Typography Scale Section */}
      <section
        id="typography"
        className="py-20 px-6 bg-[var(--bg-secondary)] border-y border-[var(--border-hairline)] transition-colors"
      >
        <div className="max-w-[980px] mx-auto space-y-12">
          <SectionHeading
            align="left"
            eyebrow="Typography"
            title="San Francisco & Inter typographic hierarchy"
            subtitle="Sentence case headings with tight tracking and balanced line heights carry the entire visual weight."
          />

          <div className="space-y-8 bg-[var(--bg-elevated)] p-8 sm:p-10 rounded-[22px] border border-[var(--border-hairline)] shadow-[var(--shadow-card)]">
            {/* Hero Scale */}
            <div className="space-y-1 pb-6 border-b border-[var(--border-hairline)]">
              <span className="text-[11px] font-mono uppercase text-[var(--text-tertiary)]">
                Hero Headline • 56px–72px • Semibold (600)
              </span>
              <p className="text-[44px] sm:text-[56px] font-semibold tracking-[-0.03em] leading-[1.05] text-[var(--text-primary)]">
                Think in days, not hours.
              </p>
            </div>

            {/* Section Scale */}
            <div className="space-y-1 pb-6 border-b border-[var(--border-hairline)]">
              <span className="text-[11px] font-mono uppercase text-[var(--text-tertiary)]">
                Section Heading • 32px–44px • Semibold (600)
              </span>
              <p className="text-[28px] sm:text-[36px] font-semibold tracking-[-0.02em] leading-[1.15] text-[var(--text-primary)]">
                Effortless daily planning.
              </p>
            </div>

            {/* Subsection Scale */}
            <div className="space-y-1 pb-6 border-b border-[var(--border-hairline)]">
              <span className="text-[11px] font-mono uppercase text-[var(--text-tertiary)]">
                Subsection Title • 21px–24px • Semibold (600)
              </span>
              <p className="text-[21px] font-semibold tracking-tight text-[var(--text-primary)]">
                Deterministic interval packing
              </p>
            </div>

            {/* Body */}
            <div className="space-y-1 pb-6 border-b border-[var(--border-hairline)]">
              <span className="text-[11px] font-mono uppercase text-[var(--text-tertiary)]">
                Body Default • 17px • Regular (400) • 1.47 Line Height
              </span>
              <p className="text-[17px] leading-[1.47] text-[var(--text-secondary)] font-normal max-w-2xl">
                Unlike ungrounded LLM assistants, NeuroFlow combines natural language intelligence with a strictly deterministic scheduler that respects your working hours and human rest buffers.
              </p>
            </div>

            {/* Small / Footnote */}
            <div className="space-y-1">
              <span className="text-[11px] font-mono uppercase text-[var(--text-tertiary)]">
                Small / Footnote • 12px–14px • Regular / Medium
              </span>
              <p className="text-[13px] text-[var(--text-tertiary)]">
                All timestamps stored in UTC. Localized based on user preferences.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Color Tokens Showcase */}
      <section className="py-20 px-6 max-w-[1200px] mx-auto space-y-12">
        <SectionHeading
          align="left"
          eyebrow="Color Palette"
          title="Monochrome neutrals with precision accents"
          subtitle="Color is used sparingly. Restrained desaturated tones communicate status and categories without visual noise."
        />

        {/* Core Palette */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-5 rounded-[18px] bg-[var(--bg-elevated)] border border-[var(--border-hairline)] space-y-2 shadow-[var(--shadow-card)]">
            <div className="h-10 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-subtle)]" />
            <p className="text-[13px] font-semibold text-[var(--text-primary)]">Canvas</p>
            <p className="text-[11px] font-mono text-[var(--text-secondary)]">Primary BG</p>
          </div>

          <div className="p-5 rounded-[18px] bg-[var(--bg-elevated)] border border-[var(--border-hairline)] space-y-2 shadow-[var(--shadow-card)]">
            <div className="h-10 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-hairline)]" />
            <p className="text-[13px] font-semibold text-[var(--text-primary)]">Secondary</p>
            <p className="text-[11px] font-mono text-[var(--text-secondary)]">Alternating BG</p>
          </div>

          <div className="p-5 rounded-[18px] bg-[var(--bg-elevated)] border border-[var(--border-hairline)] space-y-2 shadow-[var(--shadow-card)]">
            <div className="h-10 rounded-xl bg-[var(--accent)]" />
            <p className="text-[13px] font-semibold text-[var(--text-primary)]">Accent Blue</p>
            <p className="text-[11px] font-mono text-[var(--text-secondary)]">#0071e3 / #2997ff</p>
          </div>

          <div className="p-5 rounded-[18px] bg-[var(--bg-elevated)] border border-[var(--border-hairline)] space-y-2 shadow-[var(--shadow-card)]">
            <div className="h-10 rounded-xl bg-[var(--text-primary)]" />
            <p className="text-[13px] font-semibold text-[var(--text-primary)]">Primary Text</p>
            <p className="text-[11px] font-mono text-[var(--text-secondary)]">#1d1d1f / #f5f5f7</p>
          </div>
        </div>

        {/* Category Soft Colors */}
        <div className="space-y-3">
          <p className="text-[13px] font-medium text-[var(--text-secondary)] uppercase tracking-wider">
            Restrained Category & Timeline Tones
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { label: "Soft Blue", variant: "blue" },
              { label: "Soft Green", variant: "green" },
              { label: "Soft Orange", variant: "orange" },
              { label: "Soft Purple", variant: "purple" },
              { label: "Soft Pink", variant: "pink" },
              { label: "Soft Teal", variant: "teal" },
            ].map((item) => (
              <div
                key={item.variant}
                className="p-4 rounded-2xl bg-[var(--bg-elevated)] border border-[var(--border-hairline)] flex flex-col items-center justify-center gap-2"
              >
                <Badge variant={item.variant as any} dot>
                  {item.label}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 4. Interactive Components Showcase */}
      <section className="py-20 px-6 bg-[var(--bg-secondary)] border-t border-[var(--border-hairline)] transition-colors">
        <div className="max-w-[1200px] mx-auto space-y-16">
          <SectionHeading
            align="left"
            eyebrow="Components"
            title="The foundational UI component library"
            subtitle="Every component is accessible, respects system light/dark appearance, and uses thin 1.5px stroke icons."
          />

          {/* Grid of Component Showcases */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* 4.1 Buttons */}
            <Card title="Buttons" subtitle="Pill-shaped filled primary, subtle outline, and text link chevron.">
              <div className="space-y-6 pt-2">
                <div className="flex flex-wrap items-center gap-3">
                  <Button variant="primary" size="lg">
                    Primary pill
                  </Button>
                  <Button variant="secondary" size="lg">
                    Secondary
                  </Button>
                  <Button variant="outline" size="lg">
                    Outline
                  </Button>
                  <Button variant="link" size="lg">
                    Learn more
                  </Button>
                </div>

                <div className="flex flex-wrap items-center gap-3 pt-2">
                  <Button variant="primary" size="md">
                    Medium
                  </Button>
                  <Button variant="primary" size="sm">
                    Small
                  </Button>
                  <Button variant="primary" size="md" loading>
                    Loading
                  </Button>
                  <Button variant="primary" size="md" disabled>
                    Disabled
                  </Button>
                </div>
              </div>
            </Card>

            {/* 4.2 Segmented Control & Toggles */}
            <Card title="Controls & Switches" subtitle="iOS segmented control and tactile spring toggles.">
              <div className="space-y-6 pt-2">
                <div>
                  <p className="text-[13px] text-[var(--text-secondary)] mb-2">Segmented tabs</p>
                  <Tabs
                    options={tabOptions}
                    activeId={activeTab}
                    onChange={setActiveTab}
                  />
                </div>

                <div className="space-y-3 pt-2">
                  <Toggle
                    checked={toggle1}
                    onChange={setToggle1}
                    label="Deterministic buffer enforcement"
                    description="Automatically reserves 10 minutes between focus sessions."
                    color="green"
                  />
                  <div className="h-px bg-[var(--border-hairline)]" />
                  <Toggle
                    checked={toggle2}
                    onChange={setToggle2}
                    label="Overload alert banners"
                    description="Display warning banner when scheduled work exceeds 8 hours."
                    color="blue"
                  />
                </div>
              </div>
            </Card>

            {/* 4.3 Form Inputs */}
            <Card title="Form Inputs" subtitle="12px radius, minimal light gray fill, and accessible focus rings.">
              <div className="space-y-4 pt-2">
                <Input
                  label="Goal description"
                  placeholder="e.g., Prepare pitch deck and financial model"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  helperText="Enter high-level goals in plain natural language."
                />

                <Input
                  label="Search tasks"
                  placeholder="Type to filter..."
                  icon={<Search className="w-4 h-4" strokeWidth={1.5} />}
                />

                <Input
                  label="Estimated duration"
                  defaultValue="90 minutes"
                  error="Estimated hours exceed maximum daily capacity."
                />
              </div>
            </Card>

            {/* 4.4 Modals, Toasts & Alerts */}
            <Card title="Dialogs & Overlays" subtitle="Frosted backdrop blurs with clean dismiss triggers.">
              <div className="space-y-4 pt-2">
                <p className="text-[14px] text-[var(--text-secondary)] leading-relaxed">
                  Modals use 16px backdrop blur and 24px corner radius. Floating pill toasts appear centered with smooth fade-and-rise motion.
                </p>

                <div className="flex flex-wrap items-center gap-3 pt-2">
                  <Button variant="secondary" onClick={() => setIsModalOpen(true)}>
                    Open modal dialog
                  </Button>
                  <Button variant="primary" onClick={() => setIsToastOpen(true)}>
                    Trigger toast message
                  </Button>
                </div>
              </div>
            </Card>

            {/* 4.5 Skeleton Loader */}
            <Card title="Skeleton Loaders" subtitle="Gentle placeholder shimmer during asynchronous operations.">
              <div className="space-y-4 pt-2">
                <div className="flex items-center gap-3">
                  <Skeleton variant="circular" width={44} height={44} />
                  <div className="space-y-1.5 flex-1">
                    <Skeleton variant="text" width="60%" height={14} />
                    <Skeleton variant="text" width="40%" height={12} />
                  </div>
                </div>
                <Skeleton variant="rectangular" height={80} />
                <div className="flex gap-2">
                  <Skeleton variant="pill" width={80} height={26} />
                  <Skeleton variant="pill" width={110} height={26} />
                </div>
              </div>
            </Card>

            {/* 4.6 Cards & Layout Shapes */}
            <Card
              hoverable
              eyebrow="Interactive Card"
              title="Smooth hover elevation"
              subtitle="Cards use 22px border radius, subtle hairline borders, and gentle lift on hover."
            >
              <div className="pt-2 flex items-center justify-between text-[13px] text-[var(--text-secondary)]">
                <span>Hover over this card to see soft elevation.</span>
                <ArrowRight className="w-4 h-4 text-[var(--accent)]" strokeWidth={1.5} />
              </div>
            </Card>
          </div>
        </div>
      </section>

      {/* 5. Clean Modal Dialog Preview */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Schedule adjustment proposal"
        description="The agent proposes shifting 2 non-urgent tasks to Wednesday morning."
        footer={
          <>
            <Button variant="ghost" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={() => {
                setIsModalOpen(false);
                setIsToastOpen(true);
              }}
            >
              Approve plan diff
            </Button>
          </>
        }
      >
        <div className="space-y-3 py-2">
          <div className="p-3.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-hairline)] space-y-1">
            <div className="flex items-center justify-between text-[13px] font-medium text-[var(--text-primary)]">
              <span>Synthesize beta tester feedback</span>
              <Badge variant="orange" size="sm">
                Shifted +24h
              </Badge>
            </div>
            <p className="text-[12px] text-[var(--text-secondary)]">
              Moved from Tuesday 4:00 PM to Wednesday 10:00 AM to respect working hour limits.
            </p>
          </div>
        </div>
      </Modal>

      {/* 6. Floating Toast Notification */}
      <Toast
        isOpen={isToastOpen}
        onClose={() => setIsToastOpen(false)}
        message="Plan diff approved and committed."
        type="success"
      />

      {/* Footer */}
      <footer className="py-16 px-6 border-t border-[var(--border-hairline)] text-center text-[12px] text-[var(--text-tertiary)] space-y-2">
        <p>NeuroFlow Design System • Clean, minimal, spacious, premium.</p>
        <p>Documented in /frontend/DESIGN.md</p>
      </footer>
    </div>
  );
}
