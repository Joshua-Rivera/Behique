"use client";

import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Check, Globe, Loader2, Search, BookOpen, Send, Square, Trash2 } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { PageHeader } from "@/components/app-shell";
import { Answer } from "@/components/ask/answer";
import { useAsk, type Step, type Turn } from "@/components/ask/use-ask";
import { Preview, type PreviewTarget } from "@/components/preview/preview";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Sheet } from "@/components/ui/sheet";
import { useHealth } from "@/lib/api/hooks";
import type { Citation } from "@/lib/api/types";
import { cn } from "@/lib/cn";

const STEP_ICON: Record<string, typeof Search> = {
  search: Search,
  read: BookOpen,
  web_search: Globe,
  web_fetch: Globe,
};

function Timeline({ steps, running }: { steps: Step[]; running: boolean }) {
  const reduce = useReducedMotion();
  if (!steps.length && !running) return null;
  return (
    <ol aria-label="Steps" className="mb-3 flex flex-col gap-1 border-l-[0.5px] border-line pl-3">
      <AnimatePresence initial={false}>
        {steps.map((s, i) => {
          const Icon = STEP_ICON[s.kind] ?? Search;
          return (
            <motion.li
              key={i}
              initial={reduce ? false : { opacity: 0, x: -4 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
              className={cn(
                "flex items-center gap-2 text-xs",
                s.kind.startsWith("web") ? "text-sea" : "text-stone",
              )}
            >
              <Icon className="size-3.5 shrink-0" aria-hidden />
              <span className="truncate">{s.label}</span>
            </motion.li>
          );
        })}
      </AnimatePresence>
      {running && (
        <li className="flex items-center gap-2 text-xs text-moss" role="status">
          <Loader2 className="size-3.5 animate-spin" aria-hidden />
          {steps.length ? "Working…" : "Thinking…"}
        </li>
      )}
    </ol>
  );
}

function UsageFooter({ turn }: { turn: Turn }) {
  const u = turn.usage;
  if (!u) return null;
  const items = [
    ["in", u.input],
    ["out", u.output],
    ["cache read", u.cache_read],
    ["web searches", u.web_searches],
    ["steps", u.steps],
  ] as const;
  return (
    <p className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-stone" aria-label="Token usage">
      {items.map(([k, v]) => (
        <span key={k}>
          <span className="tabular-nums text-ink">{v.toLocaleString()}</span> {k}
        </span>
      ))}
    </p>
  );
}

function Setup() {
  return (
    <div className="max-w-xl px-6 py-8 text-sm text-stone">
      <p className="font-serif text-lg text-ink">Ask is turned off</p>
      <p className="mt-2">
        Ask uses Claude to answer questions from your files. It is off until the server has an
        Anthropic API key. Without one, Behique never sends anything off your machine.
      </p>
      <p className="mt-3">
        To enable it, set the key and restart. Add <code>ALLOW_WEB=true</code> to also let it search
        the web.
      </p>
      <pre className="mt-3 overflow-auto border-l-2 border-ochre bg-sand px-3 py-2 font-mono text-xs text-ink">
        ANTHROPIC_API_KEY=sk-ant-… docker compose up -d
      </pre>
      <p className="mt-3">
        When you ask a question, the question and the matching snippets of your files are sent to
        Anthropic.
      </p>
    </div>
  );
}

export default function AskPage() {
  const health = useHealth();
  const { turns, ask, stop, clear, running } = useAsk();
  const [question, setQuestion] = useState("");
  const [allowWeb, setAllowWeb] = useState(false);
  const [preview, setPreview] = useState<PreviewTarget | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const webAllowed = health.data?.web_allowed ?? false;

  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("q");
    if (q) setQuestion(q);
  }, []);

  const last = turns[turns.length - 1];
  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "end" });
  }, [turns.length, last?.steps.length, last?.answer]);

  function submit(e?: FormEvent) {
    e?.preventDefault();
    const q = question.trim();
    if (!q || running) return;
    setQuestion("");
    void ask(q, webAllowed && allowWeb);
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  }

  function openLocal(c: Extract<Citation, { type: "local" }>) {
    setPreview({ fileId: c.file_id, chunkId: c.chunk_id, path: c.path });
  }

  if (health.data && !health.data.ask_enabled)
    return (
      <>
        <PageHeader title="Ask" />
        <Setup />
      </>
    );

  return (
    <div className="flex h-full flex-col">
      <PageHeader title="Ask">
        {turns.length > 0 && (
          <Button tone="stone" onClick={clear}>
            <Trash2 aria-hidden /> Clear
          </Button>
        )}
      </PageHeader>

      <div className="min-h-0 flex-1 overflow-auto" aria-live="polite">
        <div className="mx-auto max-w-3xl px-6 py-6">
          {turns.length === 0 && (
            <p className="py-10 text-center text-sm text-stone">
              Ask a question about your files. Behique searches them first and only uses the web
              when you allow it.
            </p>
          )}
          {turns.map((t) => (
            <article key={t.id} className="mb-8 border-b-[0.5px] border-line pb-6 last:border-0">
              <h2 className="mb-3 text-sm font-medium text-ink">{t.question}</h2>
              <Timeline steps={t.steps} running={t.status === "running"} />
              {t.answer && <Answer text={t.answer} citations={t.citations} onOpenLocal={openLocal} />}
              {t.status === "stopped" && <p className="text-sm text-stone">Stopped.</p>}
              {t.status === "error" && (
                <p role="alert" className="text-sm text-danger">
                  {t.error}
                </p>
              )}
              {t.capped && (
                <p className="mt-2 text-xs text-ochre">
                  Reached the step limit, so this answer may be incomplete.
                </p>
              )}
              {t.status === "done" && (
                <p className="mt-2 inline-flex items-center gap-1 text-xs text-moss">
                  <Check className="size-3.5" aria-hidden />
                  {t.webEnabled ? "Files and web" : "Files only"}
                </p>
              )}
              <UsageFooter turn={t} />
            </article>
          ))}
          <div ref={bottom} />
        </div>
      </div>

      <form onSubmit={submit} className="border-t-[0.5px] border-line px-6 py-3">
        <div className="mx-auto flex max-w-3xl flex-col gap-2">
          <label htmlFor="question" className="sr-only">
            Question
          </label>
          <textarea
            id="question"
            rows={2}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask about your files…"
            maxLength={4000}
            className="w-full resize-none border-0 border-b-[0.5px] border-line bg-transparent py-1.5 text-base text-ink placeholder:text-stone focus:border-b-clay focus:outline-none"
          />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Checkbox
                label="Allow web"
                checked={webAllowed && allowWeb}
                disabled={!webAllowed}
                onChange={(e) => setAllowWeb(e.target.checked)}
                aria-describedby="web-note"
              />
              <span id="web-note" className="text-xs text-stone">
                {webAllowed ? "Only used when your files don't answer it." : "Web access is off on this server (ALLOW_WEB)."}
              </span>
            </div>
            {running ? (
              <Button tone="danger" onClick={stop}>
                <Square aria-hidden /> Stop
              </Button>
            ) : (
              <Button type="submit" disabled={!question.trim()}>
                <Send aria-hidden /> Ask
              </Button>
            )}
          </div>
        </div>
      </form>

      <Sheet
        open={preview !== null}
        onOpenChange={(o) => !o && setPreview(null)}
        title={preview?.path ?? "Source"}
        className="p-0"
      >
        {preview && <Preview target={preview} />}
      </Sheet>
    </div>
  );
}
