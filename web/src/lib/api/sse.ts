import { API_BASE, ApiError, authHeaders, signalUnauthorized } from "./client";

export type SseEvent = { event: string; data: unknown };

/** Parse one `text/event-stream` block ("event: x\ndata: {...}"). */
export function parseBlock(block: string): SseEvent | null {
  let event = "message";
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
  }
  if (!data.length) return null;
  try {
    return { event, data: JSON.parse(data.join("\n")) };
  } catch {
    return null;
  }
}

/** POST JSON and yield Server-Sent Events until the stream ends or `signal` aborts. */
export async function* postSse(
  path: string,
  body: unknown,
  signal: AbortSignal,
): AsyncGenerator<SseEvent> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json", accept: "text/event-stream", ...authHeaders() },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    if (res.status === 401) signalUnauthorized();
    let detail = `Request failed (${res.status})`;
    try {
      const j = (await res.json()) as { detail?: unknown };
      if (typeof j.detail === "string") detail = j.detail;
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, detail);
  }
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buf = "";
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += value.replace(/\r\n/g, "\n");
      let i: number;
      while ((i = buf.indexOf("\n\n")) >= 0) {
        const ev = parseBlock(buf.slice(0, i));
        buf = buf.slice(i + 2);
        if (ev) yield ev;
      }
    }
    const tail = parseBlock(buf);
    if (tail) yield tail;
  } finally {
    reader.releaseLock();
  }
}
