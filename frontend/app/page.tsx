"use client";

import { useEffect, useRef, useState } from "react";

// --- Types (match the SSE event shapes from backend/src/mare/api.py) ----

type Channel = {
  id: string;
  label: string;
  target_aspect: string;
  render_aspect: string;
  is_mobile_first: boolean;
  platform_notes: string;
};

type Tier = { model: string; cost: string; notes: string };

type VoiceoverBeat = { vo: string; b_roll?: string };
type Script = {
  hook: string;
  duration_seconds?: number;
  self_critique?: string;
  voiceover: VoiceoverBeat[];
  on_screen_text: string[];
  caption: string;
  hashtags: string[];
};

type RenderedBeat = {
  beat: number;
  image_url: string;
  prompt: string;
  subject: string;
};

type StatusMsg = string;

type SseEvent =
  | { type: "status"; message: string }
  | { type: "script"; script: Script }
  | { type: "prompts"; prompts: unknown }
  | { type: "beat"; beat: number; image_url: string; prompt: string; subject: string }
  | { type: "done"; slug: string; channel_id: string; beat_count: number; artifact_dir: string }
  | { type: "error"; message: string };

// Next.js dev rewrites buffer streaming responses (SSE sits idle for 45+s
// until the whole stream completes). Hit the backend directly for /api/render
// and artifact URLs; other small JSON endpoints can use the rewrite.
const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

// --- Main page ---------------------------------------------------------

export default function Home() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [tiers, setTiers] = useState<Record<string, Tier>>({});
  const [vertex, setVertex] = useState<null | {
    project: string | null;
    text: boolean;
    images: boolean;
    auth_mode: string | null;
  }>(null);

  // Form state
  const [topic, setTopic] = useState("The mirror test for scalp health");
  const [audience, setAudience] = useState("high_end_client");
  const [proof, setProof] = useState("");
  const [cta, setCta] = useState("");
  const [channelId, setChannelId] = useState("youtube_short");
  const [tier, setTier] = useState<"fast" | "standard" | "ultra">("standard");

  // Render state
  const [isRendering, setIsRendering] = useState(false);
  const [statusLog, setStatusLog] = useState<StatusMsg[]>([]);
  const [script, setScript] = useState<Script | null>(null);
  const [beats, setBeats] = useState<RenderedBeat[]>([]);
  const [doneInfo, setDoneInfo] = useState<null | {
    slug: string;
    beat_count: number;
  }>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Load channels + tiers + health on mount
  useEffect(() => {
    void fetch("/api/channels")
      .then((r) => r.json())
      .then(setChannels)
      .catch(() => {});
    void fetch("/api/tiers")
      .then((r) => r.json())
      .then(setTiers)
      .catch(() => {});
    void fetch("/api/health")
      .then((r) => r.json())
      .then((h) => setVertex(h.vertex))
      .catch(() => {});
  }, []);

  async function handleRender(e: React.FormEvent) {
    e.preventDefault();
    if (isRendering) return;

    // Reset
    setIsRendering(true);
    setError(null);
    setStatusLog([]);
    setScript(null);
    setBeats([]);
    setDoneInfo(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch("/api/render", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify({
          topic,
          audience,
          proof_point: proof || null,
          call_to_action: cta || null,
          channel: channelId,
          tier,
        }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        throw new Error(`Render failed: HTTP ${res.status}`);
      }

      // Parse SSE by hand — we use fetch (not EventSource) so we can POST a
      // JSON body. Raw Uint8Array reader + manual decode avoids
      // TextDecoderStream buffering quirks seen in some Chromium builds.
      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        if (value) buffer += decoder.decode(value, { stream: true });
        // Events are delimited by blank lines. Accept both \n\n and
        // \r\n\r\n in case any middleware normalizes line endings.
        // eslint-disable-next-line no-constant-condition
        while (true) {
          const nn = buffer.indexOf("\n\n");
          const rnrn = buffer.indexOf("\r\n\r\n");
          let idx = -1;
          let delimLen = 2;
          if (rnrn !== -1 && (nn === -1 || rnrn < nn)) {
            idx = rnrn;
            delimLen = 4;
          } else if (nn !== -1) {
            idx = nn;
            delimLen = 2;
          }
          if (idx === -1) break;
          const rawEvt = buffer.slice(0, idx);
          buffer = buffer.slice(idx + delimLen);
          const dataLine = rawEvt
            .split("\n")
            .find((l) => l.startsWith("data:"));
          if (!dataLine) continue;
          const payload = dataLine.slice(5).trim();
          if (!payload) continue;
          try {
            const evt = JSON.parse(payload) as SseEvent;
            handleEvent(evt);
          } catch {
            // ignore keepalives / malformed
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setError((err as Error).message);
      }
    } finally {
      setIsRendering(false);
      abortRef.current = null;
    }
  }

  function handleEvent(evt: SseEvent) {
    switch (evt.type) {
      case "status":
        setStatusLog((l) => [...l, evt.message]);
        break;
      case "script":
        setScript(evt.script);
        break;
      case "prompts":
        // We don't render prompts separately in the MVP — the per-beat prompt
        // is shown under each image in the gallery.
        break;
      case "beat":
        setBeats((b) => [
          ...b,
          {
            beat: evt.beat,
            image_url: evt.image_url,
            prompt: evt.prompt,
            subject: evt.subject,
          },
        ]);
        break;
      case "done":
        setDoneInfo({ slug: evt.slug, beat_count: evt.beat_count });
        break;
      case "error":
        setError(evt.message);
        break;
    }
  }

  function cancelRender() {
    abortRef.current?.abort();
  }

  return (
    <main className="min-h-screen bg-light">
      {/* --- Top bar --- */}
      <header className="bg-linen border-b border-brown-100/70">
        <div className="mx-auto max-w-7xl px-6 py-8 flex items-baseline justify-between">
          <div className="flex items-baseline gap-3">
            <span
              className="font-display text-3xl text-key tracking-tight-4"
              style={{ lineHeight: 1.12 }}
            >
              MaRe
            </span>
            <span className="text-sm text-dark/70 tracking-tight-4">Studio</span>
          </div>
          <VertexBadge vertex={vertex} />
        </div>
      </header>

      {/* --- Hero strap --- */}
      <section className="bg-linen">
        <div className="mx-auto max-w-7xl px-6 pt-6 pb-10">
          <h1
            className="font-display text-5xl md:text-6xl text-extra-dark"
            style={{ lineHeight: 1.05, letterSpacing: "-0.02em" }}
          >
            The content engine
            <span className="text-key">, rendered.</span>
          </h1>
          <p className="mt-4 max-w-2xl text-base text-dark/80 tracking-tight-4">
            A creative brief goes in. A MaRe-Verified Short, on-brand image prompts,
            and cinematic frames come out &mdash; mobile-first, 9:16, rendered through
            Google&rsquo;s Imagen 4 on Vertex AI.
          </p>
        </div>
        <div className="rule-etched" />
      </section>

      {/* --- Two-pane workspace --- */}
      <section className="mx-auto max-w-7xl px-6 py-10 grid lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)] gap-10">
        {/* Left: creative brief form */}
        <form onSubmit={handleRender} className="space-y-7">
          <FormHeader>Creative brief</FormHeader>

          <Field label="Topic" hint="One idea, one sentence. The Hook, not the title.">
            <textarea
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              rows={2}
              required
              minLength={4}
              maxLength={120}
              className="w-full resize-none rounded-md border border-brown-200/70 bg-white px-3 py-2 text-sm focus:border-key focus:outline-none focus:ring-2 focus:ring-key/20"
            />
          </Field>

          <Field label="Audience">
            <select
              value={audience}
              onChange={(e) => setAudience(e.target.value)}
              className="w-full rounded-md border border-brown-200/70 bg-white px-3 py-2 text-sm focus:border-key focus:outline-none focus:ring-2 focus:ring-key/20"
            >
              <option value="high_end_client">High-end client</option>
              <option value="salon_owner">Salon owner</option>
              <option value="stylist">Stylist</option>
              <option value="scalp_curious">Scalp-curious consumer</option>
            </select>
          </Field>

          <Field label="Proof point" hint="Optional. Grounds the claim.">
            <textarea
              value={proof}
              onChange={(e) => setProof(e.target.value)}
              rows={2}
              maxLength={400}
              placeholder="e.g. Italian-grown botanical complex, 48-hour ritual protocol…"
              className="w-full resize-none rounded-md border border-brown-200/70 bg-white px-3 py-2 text-sm placeholder:text-brown-300 focus:border-key focus:outline-none focus:ring-2 focus:ring-key/20"
            />
          </Field>

          <Field label="Call to action" hint="Optional.">
            <input
              value={cta}
              onChange={(e) => setCta(e.target.value)}
              maxLength={160}
              placeholder="e.g. Book your MaRe consultation."
              className="w-full rounded-md border border-brown-200/70 bg-white px-3 py-2 text-sm placeholder:text-brown-300 focus:border-key focus:outline-none focus:ring-2 focus:ring-key/20"
            />
          </Field>

          <Field label="Channel">
            <div className="grid grid-cols-2 gap-2">
              {channels.map((c) => (
                <ChannelChip
                  key={c.id}
                  channel={c}
                  selected={channelId === c.id}
                  onSelect={() => setChannelId(c.id)}
                />
              ))}
              {channels.length === 0 && (
                <span className="col-span-2 text-xs text-brown-400">
                  Loading channels…
                </span>
              )}
            </div>
          </Field>

          <Field label="Render tier">
            <div className="space-y-2">
              {(["fast", "standard", "ultra"] as const).map((t) => {
                const meta = tiers[t];
                return (
                  <label
                    key={t}
                    className={[
                      "flex items-start gap-3 rounded-md border px-3 py-2.5 cursor-pointer transition-all",
                      tier === t
                        ? "border-key bg-water-50"
                        : "border-brown-100 bg-white hover:border-brown-300",
                    ].join(" ")}
                  >
                    <input
                      type="radio"
                      name="tier"
                      value={t}
                      checked={tier === t}
                      onChange={() => setTier(t)}
                      className="mt-1 accent-key"
                    />
                    <div className="flex-1">
                      <div className="flex items-baseline justify-between">
                        <span className="font-semibold capitalize text-sm text-extra-dark">
                          {t}
                        </span>
                        <span className="text-xs font-medium text-key">
                          {meta?.cost ?? ""}
                        </span>
                      </div>
                      <p className="mt-0.5 text-xs text-dark/70 leading-snug">
                        {meta?.notes ?? ""}
                      </p>
                    </div>
                  </label>
                );
              })}
            </div>
          </Field>

          <div className="pt-2">
            {!isRendering ? (
              <button
                type="submit"
                className="w-full rounded-md bg-key text-light font-semibold py-3 px-4 tracking-tight-4 hover:bg-water-600 transition-colors disabled:opacity-50"
                disabled={!topic || topic.length < 4}
              >
                Render Short
              </button>
            ) : (
              <button
                type="button"
                onClick={cancelRender}
                className="w-full rounded-md bg-brown-500 text-light font-semibold py-3 px-4 tracking-tight-4 hover:bg-brown-600 transition-colors"
              >
                Cancel render
              </button>
            )}
          </div>
        </form>

        {/* Right: live output */}
        <div className="space-y-8">
          <FormHeader>Output</FormHeader>

          {error && (
            <div className="rounded-md border border-brown-500/30 bg-brown-50 px-4 py-3 text-sm text-brown-700">
              <strong className="font-semibold">Render failed.</strong> {error}
            </div>
          )}

          {!isRendering && !script && !error && (
            <EmptyState />
          )}

          {(isRendering || statusLog.length > 0) && !doneInfo && (
            <StatusStream log={statusLog} active={isRendering} />
          )}

          {script && <ScriptPanel script={script} />}

          {beats.length > 0 && (
            <BeatGallery beats={beats} totalHint={script?.voiceover.length ?? 0} />
          )}

          {doneInfo && (
            <DoneStrap slug={doneInfo.slug} beatCount={doneInfo.beat_count} />
          )}
        </div>
      </section>

      <footer className="mx-auto max-w-7xl px-6 py-10 text-xs text-brown-400 tracking-tight-4">
        MaRe is the only system that fuses AI-powered scalp diagnostics,
        multisensory therapy, and European wellness rituals into one personalized
        experience.
      </footer>
    </main>
  );
}

// --- Subcomponents -----------------------------------------------------

function FormHeader({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="font-display text-2xl text-key tracking-tight-4">{children}</h2>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-1.5">
      <div className="flex items-baseline justify-between">
        <span className="text-xs font-bold uppercase tracking-[0.08em] text-brown-500">
          {label}
        </span>
        {hint && (
          <span className="text-[11px] text-brown-400 tracking-tight-4">{hint}</span>
        )}
      </div>
      {children}
    </label>
  );
}

function ChannelChip({
  channel,
  selected,
  onSelect,
}: {
  channel: Channel;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={[
        "text-left rounded-md border px-3 py-2 transition-all",
        selected
          ? "border-key bg-water-50"
          : "border-brown-100 bg-white hover:border-brown-300",
      ].join(" ")}
    >
      <div className="text-sm font-semibold text-extra-dark leading-tight">
        {channel.label}
      </div>
      <div className="mt-0.5 text-[11px] text-brown-400 tracking-tight-4">
        {channel.render_aspect}
        {channel.is_mobile_first ? " · mobile-first" : " · print / desktop"}
      </div>
    </button>
  );
}

function VertexBadge({
  vertex,
}: {
  vertex: { project: string | null; text: boolean; images: boolean; auth_mode: string | null } | null;
}) {
  if (!vertex || !vertex.project) {
    return (
      <span className="text-xs text-brown-400 tracking-tight-4">API: AI Studio</span>
    );
  }
  const modes = [
    vertex.text && "text",
    vertex.images && "images",
  ].filter(Boolean) as string[];
  return (
    <span className="text-xs text-key tracking-tight-4">
      Vertex AI · <span className="font-mono">{vertex.project}</span>
      {modes.length > 0 && ` · ${modes.join(" + ")}`}
    </span>
  );
}

function EmptyState() {
  return (
    <div className="rounded-md border border-dashed border-brown-200/80 bg-white/40 px-6 py-10 text-center">
      <p className="font-display text-xl text-brown-500" style={{ lineHeight: 1.12 }}>
        Fill the brief, click Render.
      </p>
      <p className="mt-2 text-sm text-brown-400 max-w-md mx-auto tracking-tight-4">
        You&rsquo;ll see the script, the per-beat image prompts, and each frame
        as it lands &mdash; live.
      </p>
    </div>
  );
}

function StatusStream({ log, active }: { log: StatusMsg[]; active: boolean }) {
  const last = log[log.length - 1];
  return (
    <div className="rounded-md border border-water-200 bg-water-50 px-4 py-3">
      <div className="flex items-center gap-2">
        {active && (
          <span className="inline-flex h-2 w-2 rounded-full bg-key animate-pulse" />
        )}
        <span className="text-sm font-semibold text-water-700">
          {active ? "Working…" : "Idle"}
        </span>
      </div>
      <p className="mt-1 text-sm text-water-900 tracking-tight-4">
        {last ?? "Connecting to renderer… (first event usually lands in 10–20s)"}
      </p>
      {log.length > 1 && (
        <details className="mt-2">
          <summary className="cursor-pointer text-[11px] uppercase tracking-[0.08em] text-water-600 hover:text-water-800">
            Full log ({log.length})
          </summary>
          <ol className="mt-2 space-y-1 text-xs text-water-700 tracking-tight-4">
            {log.map((m, i) => (
              <li key={i}>
                <span className="text-water-400 mr-2">{String(i + 1).padStart(2, "0")}</span>
                {m}
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}

function ScriptPanel({ script }: { script: Script }) {
  return (
    <article className="rounded-md border border-brown-100 bg-white p-6">
      <header className="mb-4">
        <div className="text-[11px] uppercase tracking-[0.08em] text-brown-400 font-semibold">
          Short script
        </div>
        <h3
          className="mt-1 font-display text-2xl text-extra-dark"
          style={{ lineHeight: 1.15 }}
        >
          {script.hook}
        </h3>
        {script.duration_seconds && (
          <p className="mt-1 text-xs text-brown-400">
            Est. {script.duration_seconds}s
          </p>
        )}
      </header>

      <section className="space-y-3">
        {script.voiceover.map((beat, i) => (
          <div
            key={i}
            className="border-l-2 border-key/30 pl-4 py-1"
          >
            <div className="text-[11px] uppercase tracking-[0.08em] text-key font-bold">
              Beat {i + 1}
            </div>
            <p className="mt-1 text-sm text-extra-dark">{beat.vo}</p>
            {beat.b_roll && (
              <p className="mt-1 text-xs text-brown-400 italic tracking-tight-4">
                B-roll — {beat.b_roll}
              </p>
            )}
          </div>
        ))}
      </section>

      <div className="mt-5 pt-4 border-t border-brown-100 flex flex-wrap gap-2">
        {script.hashtags.map((h) => (
          <span
            key={h}
            className="text-[11px] text-water-700 bg-water-50 px-2 py-0.5 rounded"
          >
            #{h.replace(/^#/, "")}
          </span>
        ))}
      </div>

      <p className="mt-4 text-xs text-brown-500 italic tracking-tight-4">
        {script.caption}
      </p>
    </article>
  );
}

function BeatGallery({
  beats,
  totalHint,
}: {
  beats: RenderedBeat[];
  totalHint: number;
}) {
  return (
    <section>
      <div className="flex items-baseline justify-between mb-3">
        <h3 className="font-display text-xl text-key">Rendered frames</h3>
        <span className="text-xs text-brown-400 tracking-tight-4">
          {beats.length}
          {totalHint > 0 ? ` of ${totalHint}` : ""} rendered
        </span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {beats.map((b) => (
          <figure key={b.beat} className="space-y-2">
            <div className="relative overflow-hidden rounded-md bg-brown-900 aspect-[9/16] shadow-sm">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={b.image_url}
                alt={b.subject}
                className="h-full w-full object-cover"
              />
              <span className="absolute left-2 top-2 rounded bg-extra-dark/70 px-1.5 py-0.5 text-[10px] font-bold text-light">
                Beat {b.beat}
              </span>
            </div>
            <figcaption className="text-[11px] text-brown-500 tracking-tight-4 leading-snug line-clamp-3">
              {b.subject}
            </figcaption>
          </figure>
        ))}
      </div>
    </section>
  );
}

function DoneStrap({ slug, beatCount }: { slug: string; beatCount: number }) {
  return (
    <div className="rounded-md border border-key bg-water-50 px-5 py-4 flex items-center justify-between">
      <div>
        <div className="text-sm font-semibold text-key">Render complete.</div>
        <p className="mt-0.5 text-xs text-water-700 tracking-tight-4">
          {beatCount} frame{beatCount === 1 ? "" : "s"} ready to review ·{" "}
          <span className="font-mono">{slug}</span>
        </p>
      </div>
      <span className="text-[11px] text-water-600 uppercase tracking-[0.08em]">
        Awaiting MaRe-Verified review
      </span>
    </div>
  );
}
