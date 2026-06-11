// Resolve the backend base URL with this precedence:
//   1. PUBLIC_API_BASE env var (set by vercel.json on deploy) — always wins.
//   2. If running in a browser on a non-localhost host → the deployed Render backend
//      (safety net so a production build can never accidentally call localhost).
//   3. Otherwise → local dev backend.
const PROD_API_BASE = "https://gitsyntropy.onrender.com/api/v1";
const LOCAL_API_BASE = "http://localhost:8000/api/v1";

function resolveApiBase(): string {
  const explicit = import.meta.env.PUBLIC_API_BASE;
  if (explicit) return explicit;
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    const isLocal = host === "localhost" || host === "127.0.0.1" || host === "[::1]";
    return isLocal ? LOCAL_API_BASE : PROD_API_BASE;
  }
  return LOCAL_API_BASE;
}

const API_BASE = resolveApiBase();

// Simple in-memory TTL cache for GET requests
const _cache = new Map<string, { data: unknown; expiresAt: number }>();
function cached<T>(key: string, ttlMs: number, fn: () => Promise<T>): Promise<T> {
  const hit = _cache.get(key);
  if (hit && hit.expiresAt > Date.now()) return Promise.resolve(hit.data as T);
  return fn().then((data) => {
    _cache.set(key, { data, expiresAt: Date.now() + ttlMs });
    return data;
  });
}
export function bustCache(keyPrefix?: string) {
  if (!keyPrefix) { _cache.clear(); return; }
  for (const k of _cache.keys()) { if (k.startsWith(keyPrefix)) _cache.delete(k); }
}

export type HealthResponse = { status: string; service: string; version: string };
export type AnalysisResponse = { run_id: string; team_id: string; status: string; score: number; summary: string };
export type AuthResponse = {
  access_token: string;
  expires_in: number;
  user_id: string;
  token_type: string;
  github_handle?: string;
  github_name?: string;
  github_avatar_url?: string;
  is_superadmin?: boolean;
};
export type UserProfileResponse = {
  user_id: string;
  github_handle?: string;
  github_name?: string;
  github_avatar_url?: string;
  github_email?: string;
  is_superadmin?: boolean;
  created_at?: string;
};
export type AdminUserResponse = {
  user_id: string;
  github_handle?: string;
  github_name?: string;
  github_avatar_url?: string;
  github_email?: string;
  is_superadmin?: boolean;
  created_at?: string;
  last_seen_at?: string;
  team_count: number;
  assessment_complete: boolean;
  github_syncs: number;
  agent_runs: number;
};
export type AdminStatsResponse = {
  total_users: number;
  total_teams: number;
  total_assessments: number;
  total_github_syncs: number;
  total_agent_runs: number;
  best_team_name: string;
  best_team_score: number;
};
export type GithubStartResponse = {
  provider: "github";
  authorization_url: string;
  state: string;
  redirect_uri: string;
  scopes: string[];
};
export type AuthSessionResponse = {
  authenticated: boolean;
  user_id: string;
  expires_at: string;
};
export type GithubSyncResponse = {
  sync_id: string;
  user_id: string;
  github_handle: string;
  chronotype: "owl" | "lark" | "balanced" | "daytime" | "evening" | "flexible";
  activity_rhythm_score: number;
  collaboration_index: number;
  prs_last_30_days: number;
  commits_last_30_days: number;
  status: "queued" | "syncing" | "complete";
  started_at: string;
  updated_at: string;
  completed_at: string | null;
  is_mock?: boolean;
};
export type AssessmentQuestion = {
  id: string;
  prompt: string;
  left_label: string;
  right_label: string;
  dimension: string;
};
export type AssessmentSubmitResponse = {
  user_id: string;
  scores: Record<string, number>;
  answered_count: number;
  total_questions: number;
  missing_question_ids: string[];
  complete: boolean;
  submitted_at: string | null;
};
export type CompatibilityResponse = {
  member_a: string;
  member_b: string;
  total_score_36: number;
  score_pct_100: number;
  level: "excellent" | "good" | "fair" | "poor";
  label: string;
  weak_dimensions: string[];
  strong_dimensions: string[];
  risk_flags: string[];
  confidence: number;
  data_gaps: string[];
  dimension_scores: Record<string, number>;
  dimension_breakdown: Array<{
    dimension: string;
    weight: number;
    score: number;
    pct_of_weight: number;
    status: "weak" | "balanced" | "strong";
  }>;
};
export type OrchestratorResponse = {
  run_id: string;
  state: "started" | "running" | "completed";
  steps: string[];
};
export type OrchestratorStreamStatus = "queued" | "running" | "completed" | "error";
export type OrchestratorStreamEvent = {
  run_id: string;
  step: string;
  status: OrchestratorStreamStatus;
  progress_pct: number;
  message?: string;
  data?: Record<string, unknown>;
  timestamp?: string;
};
export type InsightResponse = {
  run_id: string;
  narrative: string;
  recommendations: string[];
  uncertainty_note: string;
};
export type TeamMember = {
  team_id: string;
  user_id: string;
  role: string | null;
  github_handle: string | null;
  joined_at: string;
};
export type Team = {
  id: string;
  name: string;
  description: string | null;
  created_by: string | null;
  invite_token: string | null;
  created_at: string;
  members: TeamMember[];
};
export type UserSearchResult = {
  user_id: string;
  github_handle?: string | null;
  display_name?: string | null;
  github_avatar_url?: string | null;
};
export type TeammateRecommendation = {
  user_id: string;
  github_handle: string | null;
  github_name: string | null;
  score: number;
  directional_to_seeker: number;
  directional_from_seeker: number;
};
export type TeammateRecommendationsResponse = {
  seeker_id: string;
  method: "content" | "matrix_factorization" | "hybrid";
  candidate_pool_size: number;
  recommendations: TeammateRecommendation[];
  cold_start: boolean;
};
export type CandidateSimulateResponse = {
  n_iterations: number;
  optimal_profile: Record<string, number>;
  mean_improvement: number;
  best_improvement: number;
  p25_improvement: number;
  p75_improvement: number;
  weak_dimensions_targeted: string[];
  confidence: number;
  status: string;
};
export type TeamReportResponse = {
  id: string;
  team_id: string;
  team_name: string;
  score: number;
  resilience_score: number;
  summary: string;
  created_at: string;
};
export type AgentTraceEvent = {
  step: string;
  status: string;
  progress_pct: number;
  message?: string | null;
  timestamp: string;
  duration_ms?: number | null;
  data?: Record<string, unknown> | null;
};
export type AgentRunTraceResponse = {
  id: string;
  team_id: string;
  team_name: string;
  user_id: string;
  github_handle?: string | null;
  include_candidates: boolean;
  status: string;
  error?: string | null;
  started_at: string;
  completed_at?: string | null;
  event_count: number;
  total_duration_ms?: number | null;
  agent_events: AgentTraceEvent[];
};

async function requestVoid(path: string, init?: RequestInit): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}`);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}`);
  }
  return (await res.json()) as T;
}

async function authedRequest<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  return request<T>(path, {
    ...init,
    headers: { Authorization: `Bearer ${token}`, ...(init?.headers ?? {}) },
  });
}

async function authedRequestVoid(path: string, token: string, init?: RequestInit): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}`);
  }
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  mockAnalysis: (teamId: string) =>
    request<AnalysisResponse>("/analysis/mock", { method: "POST", body: JSON.stringify({ team_id: teamId }) }),
  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  githubStart: () => request<GithubStartResponse>("/auth/github/start"),
  githubCallback: (code: string, state?: string) =>
    request<AuthResponse>("/auth/github/callback", {
      method: "POST",
      body: JSON.stringify({ code, state: state ?? null })
    }),
  session: (token: string) =>
    request<AuthSessionResponse>("/auth/session", {
      headers: { Authorization: `Bearer ${token}` }
    }),
  githubSync: (github_handle: string, token: string) =>
    authedRequest<GithubSyncResponse>("/github/sync", token, {
      method: "POST",
      body: JSON.stringify({ github_handle })
    }),
  githubSyncStatus: (sync_id: string) => request<GithubSyncResponse>(`/github/sync/${sync_id}`),
  assessmentQuestions: () => request<AssessmentQuestion[]>("/assessment/questions"),
  assessmentResponse: (user_id: string, token: string) =>
    cached(`/assessment/responses/${user_id}`, 30_000, () => authedRequest<AssessmentSubmitResponse>(`/assessment/responses/${user_id}`, token)),
  submitAssessment: (user_id: string, answers: Record<string, number>, token: string) =>
    authedRequest<AssessmentSubmitResponse>("/assessment/responses", token, {
      method: "POST",
      body: JSON.stringify({ user_id, answers })
    }).then((r) => { bustCache(`/assessment/responses/${user_id}`); return r; }),
  compatibility: (memberA: string, memberB: string, dataMode: "full" | "incomplete" = "full") =>
    request<CompatibilityResponse>("/compatibility/run", {
      method: "POST",
      body: JSON.stringify({ member_a: memberA, member_b: memberB, data_mode: dataMode })
    }),
  orchestratorRun: (team_id: string, user_id: string, token: string, include_candidates = false) =>
    authedRequest<OrchestratorResponse>("/orchestrator/run", token, {
      method: "POST",
      body: JSON.stringify({ team_id, user_id, include_candidates })
    }),
  synthesis: () => request<InsightResponse>("/insights/synthesis"),

  // Teams
  createTeam: (name: string, description: string | null, created_by: string, token: string) =>
    authedRequest<Team>("/teams", token, {
      method: "POST",
      body: JSON.stringify({ name, description, created_by }),
    }).then((t) => { bustCache("/teams"); return t; }),
  listTeams: (user_id: string, token: string) =>
    cached(`/teams?user_id=${user_id}`, 30_000, () => authedRequest<Team[]>(`/teams?user_id=${encodeURIComponent(user_id)}`, token)),
  getTeam: (team_id: string) =>
    cached(`/teams/${team_id}`, 15_000, () => request<Team>(`/teams/${team_id}`)),
  updateTeam: (team_id: string, token: string, name?: string, description?: string) =>
    authedRequest<Team>(`/teams/${team_id}`, token, {
      method: "PATCH",
      body: JSON.stringify({ name: name ?? null, description: description ?? null }),
    }).then((t) => { bustCache("/teams"); return t; }),
  addMember: (team_id: string, user_id: string, token: string, github_handle?: string, role?: string) =>
    authedRequest<TeamMember>(`/teams/${team_id}/members`, token, {
      method: "POST",
      body: JSON.stringify({ user_id, github_handle: github_handle ?? null, role: role ?? null }),
    }).then((m) => { bustCache("/teams"); return m; }),
  removeMember: (team_id: string, user_id: string, token: string) =>
    authedRequestVoid(`/teams/${team_id}/members/${encodeURIComponent(user_id)}`, token, { method: "DELETE" })
      .then(() => { bustCache("/teams"); }),
  teamRecommendations: (team_id: string, seeker_id: string, token: string, k = 5) =>
    authedRequest<TeammateRecommendationsResponse>(
      `/teams/${team_id}/recommendations?seeker_id=${encodeURIComponent(seeker_id)}&k=${k}`,
      token,
    ),
  candidateSimulate: (team_scores: Record<string, number>[], n_iterations = 1000) =>
    request<CandidateSimulateResponse>("/candidates/simulate", {
      method: "POST",
      body: JSON.stringify({ team_scores, n_iterations }),
    }),
  teamReports: (team_id: string) => request<TeamReportResponse[]>(`/teams/${team_id}/reports`),
  report: (report_id: string) => request<TeamReportResponse>(`/reports/${encodeURIComponent(report_id)}`),

  // Authenticated user profile
  me: (token: string) => authedRequest<UserProfileResponse>("/users/me", token),
  updateDisplayName: (token: string, display_name: string | null) =>
    authedRequest<UserProfileResponse>("/users/me/display-name", token, {
      method: "PATCH",
      body: JSON.stringify({ display_name }),
    }),

  // User search
  searchUsers: (q: string, token: string) => authedRequest<UserSearchResult[]>(`/users/search?q=${encodeURIComponent(q)}`, token),

  // Admin (superadmin only)
  adminStats: (token: string) =>
    cached("/admin/stats", 60_000, () => authedRequest<AdminStatsResponse>("/admin/stats", token)),
  adminUsers: (token: string) =>
    cached("/admin/users", 60_000, () => authedRequest<AdminUserResponse[]>("/admin/users", token)),
  adminAgentRuns: (token: string) =>
    cached("/admin/agent-runs", 30_000, () => authedRequest<AgentRunTraceResponse[]>("/admin/agent-runs", token)),
};

export const wsUrlForRun = (runId: string) => {
  // Same precedence as resolveApiBase: env var → host-based → local.
  let base = import.meta.env.PUBLIC_WS_BASE as string | undefined;
  if (!base) {
    if (typeof window !== "undefined") {
      const host = window.location.hostname;
      const isLocal = host === "localhost" || host === "127.0.0.1" || host === "[::1]";
      base = isLocal ? "ws://localhost:8000" : "wss://gitsyntropy.onrender.com";
    } else {
      base = "ws://localhost:8000";
    }
  }
  base = base.replace(/\/$/, "");
  return `${base}/ws/analysis/${runId}`;
};
