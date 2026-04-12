import { atom } from "nanostores";
import type { OrchestratorStreamEvent, OrchestratorStreamStatus, Team } from "./api";

export type Session = {
  userId: string;
  token: string;
  expiresIn: number;
  issuedAt: number;
  // GitHub profile (populated after OAuth)
  githubHandle?: string;
  githubName?: string;
  githubAvatarUrl?: string;
  isSuperadmin?: boolean;
};

export type SyncState = {
  syncId: string;
  githubHandle: string;
  chronotype: string;
  activityRhythmScore: number;
  collaborationIndex: number;
  status: string;
  prsLast30Days: number;
  commitsLast30Days: number;
  updatedAt: string;
};

export type CompatibilityState = {
  totalScore: number;
  label: string;
  weakDimensions: string[];
};

export type AssessmentState = {
  userId: string;
  scores: Record<string, number>;
  answeredCount: number;
  totalQuestions: number;
  missingQuestionIds: string[];
  complete: boolean;
  submittedAt: string | null;
};

export type OrchestratorState = {
  runId: string;
  currentStep: string;
  progressPct: number;
  status: OrchestratorStreamStatus;
  events: OrchestratorStreamEvent[];
};

export type TeamState = {
  teamId: string;
  memberCount: number;
};

export const $session = atom<Session | null>(null);
export const $sync = atom<SyncState | null>(null);
export const $assessmentScores = atom<Record<string, number> | null>(null);
export const $assessment = atom<AssessmentState | null>(null);
export const $compatibility = atom<CompatibilityState | null>(null);
export const $orchestrator = atom<OrchestratorState | null>(null);
export const $team = atom<TeamState | null>(null);
export const $teams = atom<Team[]>([]);
export const $activeTeam = atom<Team | null>(null);

const SESSION_STORAGE_KEY = "gitsyntropy.session";
const ACTIVE_TEAM_STORAGE_KEY = "gitsyntropy.activeTeam";

export function isSessionExpired(session: Session): boolean {
  const expiresAt = session.issuedAt + session.expiresIn * 1000;
  return Date.now() >= expiresAt;
}

export function setSession(session: Session): void {
  $session.set(session);
  if (typeof window !== "undefined") {
    window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
  }
}

export function clearSession(): void {
  $session.set(null);
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(SESSION_STORAGE_KEY);
    window.localStorage.removeItem(ACTIVE_TEAM_STORAGE_KEY);
  }
}

export function setActiveTeam(team: Team | null): void {
  $activeTeam.set(team);
  if (typeof window !== "undefined") {
    if (team) {
      window.localStorage.setItem(ACTIVE_TEAM_STORAGE_KEY, JSON.stringify(team));
    } else {
      window.localStorage.removeItem(ACTIVE_TEAM_STORAGE_KEY);
    }
  }
}

export function hydrateActiveTeam(): void {
  if (typeof window === "undefined") return;
  const raw = window.localStorage.getItem(ACTIVE_TEAM_STORAGE_KEY);
  if (!raw) return;
  try {
    const parsed = JSON.parse(raw) as Team;
    if (parsed?.id && parsed?.name) {
      $activeTeam.set(parsed);
    }
  } catch {
    window.localStorage.removeItem(ACTIVE_TEAM_STORAGE_KEY);
  }
}

export function hydrateSession(): void {
  if (typeof window === "undefined") return;
  const raw = window.localStorage.getItem(SESSION_STORAGE_KEY);
  if (!raw) return;
  try {
    const parsed = JSON.parse(raw) as Session;
    if (!parsed?.token || !parsed?.userId || typeof parsed?.expiresIn !== "number") {
      clearSession();
      return;
    }
    if (typeof parsed.issuedAt !== "number") {
      parsed.issuedAt = Date.now();
    }
    if (isSessionExpired(parsed)) {
      clearSession();
      return;
    }
    $session.set(parsed);
  } catch {
    clearSession();
  }
}
