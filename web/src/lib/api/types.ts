/** Response shapes. Request bodies come from the generated `schema.d.ts`. */

export type Health = {
  ok: boolean;
  version: string;
  model: string;
  chunks: number;
  ask_enabled: boolean;
  web_allowed: boolean;
};

export type Source = {
  id: number;
  name: string;
  path: string;
  files: number;
  chunks: number;
  last_indexed_at: number | null;
};

export type IndexStatus = {
  running: boolean;
  source_id: number | null;
  started_at: number | null;
  finished_at: number | null;
  files_seen: number;
  files_changed: number;
  files_deleted: number;
  files_failed: number;
  files_skipped: number;
  chunks_embedded: number;
  recent_errors: { path: string | null; error: string }[];
};

export type Hit = {
  chunk_id: number;
  file_id: number;
  source_id: number;
  path: string;
  start_char: number;
  end_char: number;
  heading_path: string | null;
  symbol: string | null;
  score: number;
  retrievers: string[];
  text: string;
};

export type FileView = {
  file_id: number;
  source_id: number;
  path: string;
  text: string;
  chunk_id?: number;
  start_char?: number;
  end_char?: number;
  heading_path?: string | null;
  symbol?: string | null;
};

export type Mount = { name: string; path: string; registered: boolean };

export type Citation =
  | { type: "local"; chunk_id: number; file_id: number; path: string; heading_path?: string | null }
  | { type: "web"; url: string; title?: string | null };

export type Usage = {
  input: number;
  output: number;
  cache_read: number;
  cache_write: number;
  web_searches: number;
  web_fetches: number;
  steps: number;
};

export type AskResult = {
  answer: string;
  citations: Citation[];
  usage: Usage;
  model: string;
  web_enabled: boolean;
  step_cap_reached: boolean;
  refused: boolean;
};
