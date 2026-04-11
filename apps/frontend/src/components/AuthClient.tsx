import { useStore } from "@nanostores/react";
import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { fadeInUp, slideDown, stagger } from "@/lib/motion";

import { api } from "@/lib/api";
import { $session, clearSession, setSession } from "@/lib/stores";

export function AuthClient() {
  const session = useStore($session);
  const [email, setEmail] = useState("athena@gitsyntropy.dev");
  const [password, setPassword] = useState("localdev123");
  const [oauthUrl, setOauthUrl] = useState("");
  const [oauthState, setOauthState] = useState("");
  const [isSigningIn, setIsSigningIn] = useState(false);
  const [isOAuthStarting, setIsOAuthStarting] = useState(false);
  const [isOAuthCompleting, setIsOAuthCompleting] = useState(false);
  const [authError, setAuthError] = useState("");

  const applySession = (data: { user_id: string; access_token: string; expires_in: number }) => {
    setSession({
      userId: data.user_id,
      token: data.access_token,
      expiresIn: data.expires_in,
      issuedAt: Date.now()
    });
    const next = new URLSearchParams(window.location.search).get("next");
    window.location.assign(next?.startsWith("/") ? next : "/workspace");
  };

  const runLogin = async () => {
    setAuthError("");
    setIsSigningIn(true);
    try {
      const data = await api.login(email, password);
      applySession(data);
    } catch {
      setAuthError("Email sign-in failed. Verify backend is running.");
    } finally {
      setIsSigningIn(false);
    }
  };

  const startGithubOAuth = async () => {
    setAuthError("");
    setIsOAuthStarting(true);
    try {
      const data = await api.githubStart();
      setOauthState(data.state);
      setOauthUrl(data.authorization_url);
    } catch {
      setAuthError("Unable to start GitHub OAuth.");
    } finally {
      setIsOAuthStarting(false);
    }
  };

  const completeGithubOAuth = async (code: string) => {
    setAuthError("");
    setIsOAuthCompleting(true);
    try {
      const data = await api.githubCallback(code, oauthState || undefined);
      applySession(data);
    } catch {
      setAuthError("OAuth callback failed.");
    } finally {
      setIsOAuthCompleting(false);
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    if (!code || isOAuthCompleting || session) return;
    void completeGithubOAuth(code);
    window.history.replaceState({}, "", window.location.pathname);
  }, [session, isOAuthCompleting]);

  return (
    <div className="flex flex-col lg:flex-row min-h-screen">
      {/* LEFT PANEL: Brand / Visuals */}
      <motion.div variants={fadeInUp} initial="hidden" animate="visible" className="relative hidden lg:flex w-1/2 h-full flex-col justify-center items-center overflow-hidden bg-midnight border-r border-white/40 min-h-screen">
        <div className="absolute inset-0 w-full h-full opacity-60 pointer-events-none">
          <div className="animate-float absolute top-[-10%] left-[-10%] w-[60%] h-[60%] bg-primary/40 rounded-full blur-[120px]"></div>
          <div className="animate-float absolute bottom-[-10%] right-[-10%] w-[70%] h-[70%] bg-accent-teal/30 rounded-full blur-[100px]" style={{ animationDirection: 'reverse', animationDuration: '15s' }}></div>
        </div>
        <div className="absolute inset-0 opacity-20 bg-grid-pattern"></div>
        
        <div className="relative z-10 max-w-xl px-12 flex flex-col gap-8">
          <div className="flex flex-col">
            <h1 className="text-6xl font-bold tracking-tighter leading-[0.9] text-transparent bg-clip-text bg-gradient-to-br from-white via-white to-white/40 mb-2 font-display">
              Where Data <br/>
              <span className="text-primary text-glow">Meets Flow.</span>
            </h1>
            <p className="text-gray-400 text-lg mt-4 max-w-md">
              Synchronize your engineering metrics with team sentiment for an early-warning system against burnout.
            </p>
          </div>
          
          <div className="glass-panel p-6 rounded-none relative max-w-sm mt-8">
            <div className="absolute -top-4 -right-4 bg-primary text-black text-xs font-bold px-3 py-1 rounded-full shadow-[0_0_15px_rgba(204,255,0,0.4)] animate-pulse">
              Live Sync
            </div>
            <div className="flex items-center gap-4 mb-4">
              <div className="w-10 h-10 rounded-full bg-accent-neon/20 flex items-center justify-center text-accent-neon">
                <span className="material-symbols-outlined">trending_up</span>
              </div>
              <div>
                <p className="text-sm text-gray-400 font-display uppercase tracking-wider">Velocity Predictor</p>
                <p className="text-xl font-bold font-display">+18% Team Output</p>
              </div>
            </div>
            <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-primary to-accent-neon w-[82%]"></div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* RIGHT PANEL: Auth Forms */}
      <div className="w-full lg:w-1/2 flex flex-col justify-center items-center p-8 lg:p-16 relative min-h-screen">
        <motion.div variants={slideDown} initial="hidden" animate="visible" className="w-full max-w-md relative z-10">
          <div className="mb-10 text-center lg:text-left">
            <h2 className="text-3xl font-bold mb-2 font-display">Welcome Back</h2>
            <p className="text-gray-400">Log in to view your team's sync metrics.</p>
          </div>
          
          {session ? (
            <div className="glass-card p-8 rounded-2xl flex flex-col items-center gap-4 text-center">
              <div className="w-16 h-16 rounded-full bg-accent-green/20 text-accent-neon flex items-center justify-center">
                <span className="material-symbols-outlined text-3xl">check_circle</span>
              </div>
              <h3 className="text-xl font-bold font-display">Signed in successfully</h3>
              <p className="text-gray-400">You are connected as <span className="text-white font-mono">{session.userId}</span></p>
              <button 
                className="mt-4 px-6 py-2 border border-white/40 rounded-full hover:bg-white/5 transition-colors"
                onClick={() => clearSession()}
              >
                Sign Out
              </button>
            </div>
          ) : (
            <>
              {/* GitHub Auth Button */}
              <button
                onClick={startGithubOAuth}
                disabled={isOAuthStarting || isOAuthCompleting}
                className="w-full btn btn-secondary py-3.5 px-4 flex items-center justify-center gap-3 transition-all mb-6 relative overflow-hidden"
              >
                <img src="https://upload.wikimedia.org/wikipedia/commons/9/91/Octicons-mark-github.svg" alt="GitHub" className="w-5 h-5 invert" />
                <span>
                  {isOAuthCompleting ? "Completing login..." : isOAuthStarting ? "Starting OAuth..." : "Continue with GitHub"}
                </span>
              </button>

              <div className="flex items-center gap-4 mb-6">
                <div className="h-[1px] flex-1 bg-white/10"></div>
                <span className="text-xs text-gray-500 font-mono uppercase">Or use email</span>
                <div className="h-[1px] flex-1 bg-white/10"></div>
              </div>

              {authError && (
                <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm text-center">
                  {authError}
                </div>
              )}

              <motion.form variants={stagger} initial="hidden" animate="visible" onSubmit={(e) => { e.preventDefault(); runLogin(); }} className="flex flex-col gap-4">
                <motion.div variants={fadeInUp} className="flex flex-col gap-1.5">
                  <label className="text-sm text-gray-400 font-medium ml-1">Email Address</label>
                  <input 
                    type="email" 
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.com" 
                    className="w-full bg-[#0A0A0B] border border-white/40 rounded-none px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-primary transition-all"
                  />
                </motion.div>

                <motion.div variants={fadeInUp} className="flex flex-col gap-1.5">
                  <div className="flex justify-between items-center ml-1">
                    <label className="text-sm text-gray-400 font-medium">Password</label>
                    <a href="#" className="text-xs text-primary hover:text-primary-text transition-colors">Forgot?</a>
                  </div>
                  <input 
                    type="password" 
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••" 
                    className="w-full bg-[#0A0A0B] border border-white/40 rounded-none px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-primary transition-all"
                  />
                </motion.div>

                <motion.button
                  variants={fadeInUp}
                  whileTap={{ scale: 0.97 }}
                  type="submit"
                  disabled={isSigningIn}
                  className="w-full btn btn-primary py-3.5 mt-2"
                >
                  {isSigningIn ? "Signing In..." : "Sign In to Workspace"}
                </motion.button>
              </motion.form>
              
              {oauthUrl && (
                <div className="mt-4 p-4 text-xs bg-white/5 rounded-lg border border-white/40 text-gray-400 break-all">
                  <p className="font-bold text-white mb-1">OAuth URL Generated:</p>
                  <code>{oauthUrl}</code>
                </div>
              )}
              
              <p className="text-center text-sm text-gray-500 mt-8">
                Don't have an account? <a href="#" className="text-white hover:text-primary transition-colors underline decoration-white/30 underline-offset-4">Request Access</a>
              </p>
            </>
          )}
        </motion.div>
      </div>
    </div>
  );
}