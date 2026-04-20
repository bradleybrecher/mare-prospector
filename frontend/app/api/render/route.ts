/**
 * Streaming proxy for /api/render → backend.
 *
 * Next.js `rewrites` in dev buffer streaming responses until the upstream
 * closes, which makes the Server-Sent Events dashboard look frozen. Handling
 * this as an explicit Route Handler with an explicit ReadableStream pump
 * flushes every SSE chunk to the browser the moment the backend yields it,
 * and swallows upstream close as a normal end-of-stream (not an error).
 */

import { NextRequest } from "next/server";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const body = await req.text();

  const upstream = await fetch(`${API_BASE}/api/render`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body,
    // @ts-expect-error — `duplex` is valid at runtime for streaming bodies.
    duplex: "half",
  });

  if (!upstream.ok || !upstream.body) {
    return new Response(
      JSON.stringify({ error: `Upstream ${upstream.status}` }),
      { status: upstream.status || 502, headers: { "Content-Type": "application/json" } },
    );
  }

  // Explicit ReadableStream passthrough. Two advantages over `return new
  // Response(upstream.body)`:
  //   1. Each chunk is forwarded (enqueued) the moment it arrives, so the
  //      browser doesn't wait for the pipe to close before seeing data.
  //   2. A graceful upstream close (stream ended normally) is translated to
  //      controller.close() — not thrown as "other side closed", which
  //      otherwise bubbles up as a 500 and discards the entire buffered body.
  const reader = upstream.body.getReader();
  const stream = new ReadableStream<Uint8Array>({
    async pull(controller) {
      try {
        const { value, done } = await reader.read();
        if (done) {
          controller.close();
          return;
        }
        if (value) controller.enqueue(value);
      } catch (err) {
        // Treat any read error as end-of-stream so the browser still gets
        // every byte that was flushed before the socket closed.
        console.warn("[api/render] upstream read error (treated as EOF):", err);
        controller.close();
      }
    },
    cancel() {
      void reader.cancel().catch(() => {});
    },
  });

  return new Response(stream, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
