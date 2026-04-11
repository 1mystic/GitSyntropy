import { type PropsWithChildren, useEffect, useState } from "react";
import { useStore } from "@nanostores/react";

import { api } from "@/lib/api";
import { $session, clearSession, hydrateSession, isSessionExpired } from "@/lib/stores";
import { AUTH_REQUIRED, GUEST_TRIAL_ENABLED } from "@/lib/featureFlags";

function GuestBanner() {
  const nextPath = typeof window !== "undefined" ? window.location.pathname : "/";
  return (
    <div className="fixed top-0 left-0 right-0 z-[100] flex items-center justify-between gap-4 px-4 md:px-8 py-2.5 bg-[#0A0A0B]/95 border-b border-primary/30 backdrop-blur-md">
      <div className="flex items-center gap-2 text-sm text-gray-300">
        <span className="w-2 h-2 rounded-full bg-primary animate-pulse flex-shrink-0" />
        <span>
          <span className="text-white font-medium">Guest Preview</span>
          <span className="text-gray-500 hidden sm:inline"> — Showing demo data. Sign in to see your real GitHub profile.</span>
        </span>
      </div>
      <a href={`/auth?next=${encodeURIComponent(nextPath)}`} className="btn btn-primary text-xs py-1.5 px-4 flex-shrink-0">
        Sign in with GitHub
      </a>
    </div>
  );
}

type Props = PropsWithChildren<{ strict?: boolean }>;

export function ProtectedGate({ children, strict = false }: Props) {
  // ── ALL hooks must be called unconditionally (Rules of Hooks) ──────────
  // mounted: false on server + first client render → same output → no hydration mismatch
  const [mounted, setMounted] = useState(false);
  const session = useStore($session);
  const [sessionValid, setSessionValid] = useState<boolean | null>(null);

  useEffect(() => {
    hydrateSession();
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    if (!session?.token) { setSessionValid(false); return; }
    if (isSessionExpired(session)) { clearSession(); setSessionValid(false); return; }

    api.session(session.token)
      .then(() => setSessionValid(true))
      .catch(() => { clearSession(); setSessionValid(false); });
  }, [session?.token, mounted]);
  // ── End hooks ──────────────────────────────────────────────────────────

  // Before mount: render children exactly as server did → no hydration mismatch
  if (!mounted) return <>{children}</>;

  // Dev mode — no enforcement
  if (!AUTH_REQUIRED) return <>{children}</>;

  const isAuthed = session && sessionValid === true;
  const checking = session && sessionValid === null;

  if (checking) {
    return (
      <div className="relative z-10 flex items-center justify-center min-h-screen">
        <p className="text-gray-600 text-sm">Validating session…</p>
      </div>
    );
  }

  if (!isAuthed) {
    if (strict || !GUEST_TRIAL_ENABLED) {
      const nextPath = window.location.pathname;
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
    return (
      <>
        <GuestBanner />
        <div className="pt-10">{children}</div>
      </>
    );
  }

  return <>{children}</>;
}
