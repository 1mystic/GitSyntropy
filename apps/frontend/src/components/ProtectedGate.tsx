import type { PropsWithChildren } from "react";
import { useStore } from "@nanostores/react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { $session, clearSession, isSessionExpired } from "@/lib/stores";
import { AUTH_REQUIRED, GUEST_TRIAL_ENABLED } from "@/lib/featureFlags";

/**
 * GuestBanner — shown at the top of every guest-mode page.
 * Clicking "Sign in" redirects to /auth with ?next= for return navigation.
 */
function GuestBanner() {
  const nextPath = typeof window !== "undefined" ? window.location.pathname : "/";
  return (
    <div className="fixed top-0 left-0 right-0 z-[100] flex items-center justify-between gap-4 px-4 md:px-8 py-2.5 bg-[#0A0A0B]/95 border-b border-primary/30 backdrop-blur-md">
      <div className="flex items-center gap-2 text-sm text-gray-300">
        <span className="w-2 h-2 rounded-full bg-primary animate-pulse flex-shrink-0" />
        <span>
          <span className="text-white font-medium">Guest Preview</span>
          <span className="text-gray-500 hidden sm:inline"> — Showing demo data. Sign in to analyse your real GitHub profile.</span>
        </span>
      </div>
      <a
        href={`/auth?next=${encodeURIComponent(nextPath)}`}
        className="btn btn-primary text-xs py-1.5 px-4 flex-shrink-0"
      >
        Sign in with GitHub
      </a>
    </div>
  );
}

type ProtectedGateProps = PropsWithChildren<{
  /** If true, unauthenticated visitors see a hard redirect to /auth (no guest mode). */
  strict?: boolean;
}>;

export function ProtectedGate({ children, strict = false }: ProtectedGateProps) {
  // Dev mode — no auth enforcement
  if (!AUTH_REQUIRED) {
    return <>{children}</>;
  }

  const session = useStore($session);
  const nextPath = typeof window !== "undefined" ? window.location.pathname : "/";

  const sessionQuery = useQuery({
    queryKey: ["auth-session", session?.token],
    queryFn: () => api.session(session!.token),
    enabled: Boolean(session?.token),
    retry: false,
  });

  // Expire stale sessions
  if (session && isSessionExpired(session)) {
    clearSession();
  }

  const isAuthed = session && !sessionQuery.isError && !isSessionExpired(session);

  // Hard block (strict pages) OR guest trial disabled → redirect to auth
  if (!isAuthed && (strict || !GUEST_TRIAL_ENABLED)) {
    return (
      <section className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4">
        <div className="glass-panel p-10 rounded-none w-full max-w-md text-center flex flex-col items-center gap-6">
          <span className="material-symbols-outlined text-5xl text-primary">lock</span>
          <div>
            <h3 className="text-xl font-bold font-display">Sign in required</h3>
            <p className="text-gray-400 mt-2 text-sm">Connect your GitHub account to access this page.</p>
          </div>
          <a href={`/auth?next=${encodeURIComponent(nextPath)}`} className="btn btn-primary w-full justify-center">
            <img src="https://upload.wikimedia.org/wikipedia/commons/9/91/Octicons-mark-github.svg" alt="" className="w-4 h-4 invert" />
            Sign in with GitHub
          </a>
        </div>
      </section>
    );
  }

  if (sessionQuery.isPending && session) {
    return (
      <section className="relative z-10 flex flex-col items-center justify-center min-h-screen">
        <p className="text-gray-500 text-sm">Validating session…</p>
      </section>
    );
  }

  // Guest trial — show children (with demo data) + banner
  if (!isAuthed && GUEST_TRIAL_ENABLED) {
    return (
      <>
        <GuestBanner />
        <div className="pt-10">{children}</div>
      </>
    );
  }

  return <>{children}</>;
}
