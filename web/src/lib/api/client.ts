import createClient, { type Middleware } from "openapi-fetch";

import { getApiKey } from "../settings";
import type { paths } from "./schema";

/** Empty in production (same origin). `pnpm dev` points it at the FastAPI server. */
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

export const UNAUTHORIZED_EVENT = "behique:unauthorized";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export function authHeaders(): Record<string, string> {
  const key = getApiKey();
  return key ? { "x-api-key": key } : {};
}

export function signalUnauthorized(): void {
  window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
}

const auth: Middleware = {
  onRequest({ request }) {
    for (const [k, v] of Object.entries(authHeaders())) request.headers.set(k, v);
    return request;
  },
  onResponse({ response }) {
    if (response.status === 401) signalUnauthorized();
    return response;
  },
};

export const api = createClient<paths>({ baseUrl: API_BASE });
api.use(auth);

/** Unwrap an openapi-fetch result, turning errors into ApiError. */
export async function unwrap<T>(
  p: Promise<{ data?: unknown; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await p;
  if (!response.ok) {
    const detail = (error as { detail?: unknown } | undefined)?.detail;
    throw new ApiError(
      response.status,
      typeof detail === "string" ? detail : `Request failed (${response.status})`,
    );
  }
  return data as T;
}
