const API_BASE = import.meta.env.PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

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
  chronotype: "owl" | "lark" | "balanced";
  activity_rhythm_score: number;
  collaboration_index: number;
  prs_last_30_days: number;
  commits_last_30_days: number;
  status: "queued" | "syncing" | "complete";
  started_at: string;
  updated_at: string;
  completed_at: string | null;
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
  githubSync: (github_handle: string, user_id = "user_local") =>
    request<GithubSyncResponse>("/github/sync", {
      method: "POST",
      body: JSON.stringify({ github_handle, user_id })
    }),
  githubSyncStatus: (sync_id: string) => request<GithubSyncResponse>(`/github/sync/${sync_id}`),
  assessmentQuestions: () => request<AssessmentQuestion[]>("/assessment/questions"),
  assessmentResponse: (user_id: string) => request<AssessmentSubmitResponse>(`/assessment/responses/${user_id}`),
  submitAssessment: (user_id: string, answers: Record<string, number>) =>
    request<AssessmentSubmitResponse>("/assessment/responses", {
      method: "POST",
      body: JSON.stringify({ user_id, answers })
    }),
  compatibility: (memberA: string, memberB: string, dataMode: "full" | "incomplete" = "full") =>
    request<CompatibilityResponse>("/compatibility/run", {
      method: "POST",
      body: JSON.stringify({ member_a: memberA, member_b: memberB, data_mode: dataMode })
    }),
  orchestratorRun: (team_id: string, user_id: string, include_candidates = false) =>
    request<OrchestratorResponse>("/orchestrator/run", {
      method: "POST",
      body: JSON.stringify({ team_id, user_id, include_candidates })
    }),
  synthesis: () => request<InsightResponse>("/insights/synthesis"),

  // Teams
  createTeam: (name: string, description: string | null, created_by: string) =>
    request<Team>("/teams", {
      method: "POST",
      body: JSON.stringify({ name, description, created_by }),
    }),
  listTeams: (user_id: string) => request<Team[]>(`/teams?user_id=${encodeURIComponent(user_id)}`),
  getTeam: (team_id: string) => request<Team>(`/teams/${team_id}`),
  updateTeam: (team_id: string, name?: string, description?: string) =>
    request<Team>(`/teams/${team_id}`, {
      method: "PATCH",
      body: JSON.stringify({ name: name ?? null, description: description ?? null }),
    }),
  addMember: (team_id: string, user_id: string, github_handle?: string, role?: string) =>
    request<TeamMember>(`/teams/${team_id}/members`, {
      method: "POST",
      body: JSON.stringify({ user_id, github_handle: github_handle ?? null, role: role ?? null }),
    }),
  removeMember: (team_id: string, user_id: string) =>
    requestVoid(`/teams/${team_id}/members/${encodeURIComponent(user_id)}`, { method: "DELETE" }),

  // Authenticated user profile
  me: (token: string) => authedRequest<UserProfileResponse>("/users/me", token),
  updateDisplayName: (token: string, display_name: string | null) =>
    authedRequest<UserProfileResponse>("/users/me/display-name", token, {
      method: "PATCH",
      body: JSON.stringify({ display_name }),
    }),

  // User search (no auth required — searching public handles/names)
  searchUsers: (q: string) => request<UserSearchResult[]>(`/users/search?q=${encodeURIComponent(q)}`),

  // Admin (superadmin only)
  adminStats: (token: string) => authedRequest<AdminStatsResponse>("/admin/stats", token),
  adminUsers: (token: string) => authedRequest<AdminUserResponse[]>("/admin/users", token),
};

export const wsUrlForRun = (runId: string) => {
  const base = (import.meta.env.PUBLIC_WS_BASE ?? "ws://localhost:8000").replace(/\/$/, "");
  return `${base}/ws/analysis/${runId}`;
};
