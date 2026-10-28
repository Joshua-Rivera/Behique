"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Check, KeyRound } from "lucide-react";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { PageHeader } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Tabs } from "@/components/ui/tabs";
import { useHealth } from "@/lib/api/hooks";
import {
  getApiKey,
  getDefaultMode,
  isKeyRemembered,
  MODES,
  setApiKey,
  setDefaultMode,
  type SearchMode,
} from "@/lib/settings";
import { getTheme, setTheme, type Theme } from "@/lib/theme";

const THEMES: { value: Theme; label: string }[] = [
  { value: "system", label: "System" },
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-b-[0.5px] border-line py-5">
      <h2 className="mb-3 font-serif text-lg text-ink">{title}</h2>
      {children}
    </section>
  );
}

export default function SettingsPage() {
  const qc = useQueryClient();
  const health = useHealth();
  const [key, setKey] = useState("");
  const [remember, setRemember] = useState(false);
  const [saved, setSaved] = useState(false);
  const [authReason, setAuthReason] = useState(false);
  const [theme, setThemeState] = useState<Theme>("system");
  const [mode, setMode] = useState<SearchMode>("hybrid");

  useEffect(() => {
    setKey(getApiKey());
    setRemember(isKeyRemembered());
    setThemeState(getTheme());
    setMode(getDefaultMode());
    setAuthReason(new URLSearchParams(window.location.search).get("reason") === "auth");
  }, []);

  function onSave(e: FormEvent) {
    e.preventDefault();
    setApiKey(key, remember);
    setSaved(true);
    setAuthReason(false);
    qc.invalidateQueries();
  }

  const h = health.data;
  const rows: [string, ReactNode][] = h
    ? [
        ["Version", h.version],
        ["Embedding model", h.model],
        ["Indexed chunks", h.chunks.toLocaleString()],
        ["Ask", h.ask_enabled ? "Enabled" : "Off (no ANTHROPIC_API_KEY)"],
        ["Web access", h.web_allowed ? "Allowed" : "Off (ALLOW_WEB=false)"],
      ]
    : [];

  return (
    <div className="max-w-2xl">
      <PageHeader title="Settings" />
      <div className="px-6">
        <Section title="API key">
          {authReason && (
            <p role="alert" className="mb-3 text-sm text-danger">
              This server needs an API key. Enter the value of <code>API_KEY</code> to continue.
            </p>
          )}
          <form onSubmit={onSave} className="flex flex-col gap-3">
            <label className="text-sm text-stone" htmlFor="api-key">
              Sent as the <code>X-API-Key</code> header. Only needed when the server sets{" "}
              <code>API_KEY</code>.
            </label>
            <Input
              id="api-key"
              type="password"
              autoComplete="off"
              value={key}
              onChange={(e) => {
                setKey(e.target.value);
                setSaved(false);
              }}
              placeholder="No key"
              className="max-w-sm"
            />
            <Checkbox
              label="Remember on this device"
              checked={remember}
              onChange={(e) => {
                setRemember(e.target.checked);
                setSaved(false);
              }}
            />
            <div className="flex items-center gap-3">
              <Button type="submit">
                <KeyRound aria-hidden /> Save key
              </Button>
              {saved && (
                <span role="status" className="inline-flex items-center gap-1 text-sm text-moss">
                  <Check className="size-4" aria-hidden /> Saved
                </span>
              )}
            </div>
          </form>
        </Section>

        <Section title="Appearance">
          <Tabs
            label="Theme"
            value={theme}
            options={THEMES}
            onChange={(t) => {
              setThemeState(t);
              setTheme(t);
            }}
          />
        </Section>

        <Section title="Default search mode">
          <Tabs
            label="Default search mode"
            value={mode}
            options={MODES}
            onChange={(m) => {
              setMode(m);
              setDefaultMode(m);
            }}
          />
        </Section>

        <Section title="Server">
          {health.isPending && <p className="text-sm text-stone">Loading…</p>}
          {health.isError && (
            <p className="text-sm text-danger">Could not reach the server: {health.error.message}</p>
          )}
          {h && (
            <dl className="grid grid-cols-[max-content_1fr] gap-x-8 gap-y-2 text-sm">
              {rows.map(([k, v]) => (
                <div key={k} className="contents">
                  <dt className="text-stone">{k}</dt>
                  <dd className="text-ink">{v}</dd>
                </div>
              ))}
            </dl>
          )}
        </Section>
      </div>
    </div>
  );
}
