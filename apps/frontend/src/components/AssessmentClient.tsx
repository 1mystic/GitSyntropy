import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { fadeInUp, scaleIn, slideDown, stagger } from "@/lib/motion";

import { api } from "@/lib/api";
import { $assessment, $session } from "@/lib/stores";
import { AUTH_BYPASS_USER_ID, AUTH_REQUIRED } from "@/lib/featureFlags";
import { ErrorBoundary } from "@/components/ErrorBoundary";

// English labels for each assessment dimension
const DIMENSION_CONFIG: Record<string, { label: string; description: string; weight: number }> = {
  nadi_chronotype_sync:     { label: "Chronotype Sync",       description: "Peak work-hour overlap — when energy peaks align", weight: 8 },
  bhakoot_strategy:         { label: "Stress Response",       description: "How you respond under pressure and tight deadlines", weight: 7 },
  gana_temperament:         { label: "Risk Tolerance",        description: "Bold vs cautious decision-making tendencies", weight: 6 },
  graha_maitri_cognition:   { label: "Decision Style",        description: "Data-driven vs intuitive reasoning preference", weight: 5 },
  yoni_workstyle:           { label: "Work Style",            description: "Solo-focus vs collaborative working preference", weight: 4 },
  tara_resilience:          { label: "Team Resilience",       description: "Capacity to absorb and recover from setbacks", weight: 3 },
  vashya_influence:         { label: "Leadership Orientation", description: "Tendency to lead, follow, or self-direct", weight: 2 },
  varna_alignment:          { label: "Innovation Drive",      description: "Appetite for novel approaches vs proven methods", weight: 1 },
};

// q1=varna (weight 1) ... q8=nadi (weight 8), matching backend ASHTAKOOT_WEIGHTS order
const QUESTION_DIMENSION: Record<string, (typeof DIMENSION_CONFIG)[keyof typeof DIMENSION_CONFIG]> = {
  q1: DIMENSION_CONFIG.varna_alignment,
  q2: DIMENSION_CONFIG.vashya_influence,
  q3: DIMENSION_CONFIG.tara_resilience,
  q4: DIMENSION_CONFIG.yoni_workstyle,
  q5: DIMENSION_CONFIG.graha_maitri_cognition,
  q6: DIMENSION_CONFIG.gana_temperament,
  q7: DIMENSION_CONFIG.bhakoot_strategy,
  q8: DIMENSION_CONFIG.nadi_chronotype_sync,
};

function ScoreScreen({ scores }: { scores: Record<string, number> }) {
  const dimensions = Object.entries(DIMENSION_CONFIG).sort((a, b) => b[1].weight - a[1].weight);

  return (
    <div className="w-full animate-fade-in">
      <div className="flex flex-col items-center mb-10">
        <div className="w-16 h-16 rounded-2xl bg-accent-neon/10 border border-accent-neon/30 flex items-center justify-center mb-4">
          <span className="material-symbols-outlined text-3xl text-accent-neon">verified</span>
        </div>
        <h2 className="text-3xl font-bold font-display text-white mb-1">Psychometric Profile</h2>
        <p className="text-gray-400 text-sm text-center max-w-md">
          Your baseline scores across all compatibility dimensions. These feed into the team analysis pipeline.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 mb-8">
        {dimensions.map(([key, config]) => {
          const raw = scores[key] ?? 0;
          const pct = Math.round((raw / config.weight) * 100);
          const isStrong = pct >= 70;
          const isWeak = pct <= 30;

          return (
            <div key={key} className="glass-panel rounded-none p-4 border border-white/5 flex items-center gap-4">
              <div className="w-10 h-10 flex-shrink-0 rounded-lg bg-white/5 flex items-center justify-center">
                <span className="text-xs font-bold font-mono text-primary">{config.weight}pt</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-sm font-semibold text-white">{config.label}</span>
                  <span
                    className={`text-xs font-bold px-2 py-0.5 rounded ${
                      isStrong
                        ? "text-green-400 bg-green-500/10"
                        : isWeak
                          ? "text-red-400 bg-red-500/10"
                          : "text-gray-300 bg-white/5"
                    }`}
                  >
                    {pct}%
                  </span>
                </div>
                <div className="w-full bg-white/5 rounded-full h-1.5 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${
                      isStrong
                        ? "bg-gradient-to-r from-green-500 to-accent-neon"
                        : isWeak
                          ? "bg-gradient-to-r from-red-500 to-orange-400"
                          : "bg-gradient-to-r from-primary to-accent-teal"
                    }`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <p className="text-[10px] text-gray-500 mt-1.5">{config.description}</p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex gap-3">
        <a
          href="/workspace"
          className="flex-1 btn btn-primary py-3 rounded-xl flex items-center justify-center gap-2"
        >
          <span className="material-symbols-outlined text-sm">schema</span>
          Run Team Analysis
        </a>
        <a
          href="/assessment"
          onClick={(e) => { e.preventDefault(); window.location.reload(); }}
          className="px-4 py-3 border border-white/10 rounded-xl text-sm text-gray-400 hover:bg-white/5 hover:text-white transition-all flex items-center gap-2"
        >
          <span className="material-symbols-outlined text-sm">edit</span>
          Retake
        </a>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="w-full glass-panel rounded-none p-8 md:p-12 animate-pulse">
      <div className="h-4 w-32 bg-white/10 rounded mb-8" />
      <div className="h-8 w-3/4 bg-white/10 rounded mb-4" />
      <div className="h-2 w-full bg-white/5 rounded-full mb-10" />
      <div className="space-y-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-5 bg-white/5 rounded" style={{ width: `${85 - i * 8}%` }} />
        ))}
      </div>
    </div>
  );
}

function AssessmentInner() {
  const session = $session.get();
  const userId = session?.userId ?? AUTH_BYPASS_USER_ID;

  if (AUTH_REQUIRED && !session) {
    return (
      <main className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4 pt-10 pb-12 w-full max-w-[1400px] mx-auto px-4 md:px-8">
        <section className="glass-panel p-8 rounded-none w-full text-center">
          <h3 className="text-xl font-bold font-display text-white">Authentication Required</h3>
          <p className="text-gray-400 mt-2 mb-6">Sign in on the auth page to complete the assessment.</p>
          <a href="/auth" className="btn btn-primary justify-center">Go to Sign In</a>
        </section>
      </main>
    );
  }

  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [scoreScreen, setScoreScreen] = useState(false);
  const [finalScores, setFinalScores] = useState<Record<string, number>>({});
  const [questions, setQuestions] = useState<
    { id: string; prompt: string; left_label: string; right_label: string }[]
  >([]);

  const loadData = async () => {
    setLoading(true);
    setLoadError(false);
    try {
      const [questionData, profileData] = await Promise.all([
        api.assessmentQuestions(),
        api.assessmentResponse(userId)
      ]);
      setQuestions(questionData);
      const restoredAnswers: Record<string, number> = {};
      const scoreDimensions = Object.keys(profileData.scores);
      scoreDimensions.forEach((dimension, idx) => {
        const questionId = `q${idx + 1}`;
        if (profileData.missing_question_ids.includes(questionId)) return;
        const maxWeight = idx + 1;
        const normalized = maxWeight === 0 ? 0 : profileData.scores[dimension] / maxWeight;
        restoredAnswers[questionId] = Math.max(1, Math.min(5, Math.round(normalized * 5)));
      });
      setAnswers(restoredAnswers);
      $assessment.set({
        userId: profileData.user_id,
        scores: profileData.scores,
        answeredCount: profileData.answered_count,
        totalQuestions: profileData.total_questions,
        missingQuestionIds: profileData.missing_question_ids,
        complete: profileData.complete,
        submittedAt: profileData.submitted_at
      });
    } catch {
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void loadData(); }, [userId]);

  const submitAssessment = async () => {
    setSubmitting(true);
    try {
      const data = await api.submitAssessment(userId, answers);
      $assessment.set({
        userId: data.user_id,
        scores: data.scores,
        answeredCount: data.answered_count,
        totalQuestions: data.total_questions,
        missingQuestionIds: data.missing_question_ids,
        complete: data.complete,
        submittedAt: data.submitted_at
      });
      setFinalScores(data.scores);
      setScoreScreen(true);
    } finally {
      setSubmitting(false);
    }
  };

  const totalCount = questions.length || 8;
  const answeredCount = Object.keys(answers).length;
  const progress = useMemo(() => Math.round((answeredCount / totalCount) * 100), [answeredCount, totalCount]);
  const activeQuestion = questions[currentIndex];
  const hasAllAnswers = answeredCount === totalCount;

  const selectAnswer = (questionId: string, value: number) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  if (scoreScreen) {
    return (
      <main className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4 pt-10 pb-12 w-full max-w-[1400px] mx-auto px-4 md:px-8">
        <ScoreScreen scores={finalScores} />
      </main>
    );
  }

  return (
    <motion.main variants={fadeInUp} initial="hidden" animate="visible" className="relative z-10 w-full max-w-[1400px] mx-auto px-4 md:px-8 pt-10 pb-24 flex flex-col min-h-screen">
      {/* Page header */}
      <motion.header variants={slideDown} initial="hidden" animate="visible" className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 gap-4">
        <div>
          <span className="text-primary font-mono text-xs uppercase tracking-widest mb-2 block">Psychometric Profiling</span>
          <h1 className="text-4xl md:text-5xl font-bold font-display tracking-tight text-white">Behavioral Assessment</h1>
          <p className="text-gray-400 text-sm mt-2">8 dimensions · ~5 minutes · used in compatibility scoring</p>
        </div>
        <div className="text-right flex-shrink-0">
          <span className="text-4xl font-bold font-display text-accent-neon">{progress}%</span>
          <span className="text-gray-500 text-sm block font-mono mt-0.5">Profiling: <span className="text-primary">{userId}</span></span>
        </div>
      </motion.header>

      {/* Progress bar */}
      <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden border border-white/10 mb-10">
        <div
          className="h-full bg-gradient-to-r from-primary to-accent-neon rounded-full transition-all duration-500 ease-out shadow-[0_0_10px_rgba(57,255,20,0.5)]"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Two-column layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-8">

        {/* LEFT: Question */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          {loading && <LoadingSkeleton />}

          {loadError && (
            <div className="glass-panel rounded-none p-8 text-center flex flex-col items-center gap-4">
              <span className="material-symbols-outlined text-4xl text-red-400">error_outline</span>
              <div>
                <h3 className="font-bold text-white mb-1">Failed to load assessment</h3>
                <p className="text-sm text-gray-400">Unable to reach the API. Check your backend connection.</p>
              </div>
              <button
                onClick={() => void loadData()}
                className="px-4 py-2 rounded-lg border border-white/20 text-sm text-gray-300 hover:bg-white/5 hover:text-white transition-colors flex items-center gap-2"
              >
                <span className="material-symbols-outlined text-sm">refresh</span>
                Retry
              </button>
            </div>
          )}

          <AnimatePresence mode="wait">
          {!loading && !loadError && activeQuestion && (
            <motion.div key={activeQuestion.id} variants={scaleIn} initial="hidden" animate="visible" exit={{ opacity: 0, y: -10 }} className="glass-panel rounded-none p-8 md:p-12 relative overflow-hidden group flex-1">
              <div className="absolute top-0 right-0 p-4">
                <span className="material-symbols-outlined text-white/10 text-6xl transform rotate-12 group-hover:text-primary/20 transition-colors duration-500">
                  psychology
                </span>
              </div>
              <div className="relative z-10 h-full flex flex-col">
                <span className="inline-block px-3 py-1 rounded-full bg-white/5 border border-white/40 text-xs font-bold tracking-widest text-primary mb-6 font-display uppercase">
                  Question {currentIndex + 1} of {totalCount}
                </span>
                <h2 className="text-2xl md:text-3xl font-bold text-white mb-4 font-display leading-tight">
                  {activeQuestion.prompt}
                </h2>
                {QUESTION_DIMENSION[activeQuestion.id] && (
                  <p className="text-sm text-gray-500 mb-10 leading-relaxed">
                    <span className="font-semibold text-gray-400">{QUESTION_DIMENSION[activeQuestion.id].label}</span>
                    {" — "}{QUESTION_DIMENSION[activeQuestion.id].description}
                  </p>
                )}
                <div className="relative w-full px-2 mb-8 mt-auto">
                  <input
                    type="range"
                    min="1"
                    max="5"
                    step="1"
                    value={answers[activeQuestion.id] ?? 3}
                    onChange={(e) => selectAnswer(activeQuestion.id, Number(e.target.value))}
                    className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer outline-none focus:ring-2 focus:ring-primary accent-primary"
                    style={{
                      accentColor: "var(--primary-solid)",
                      WebkitAppearance: "none",
                      background: `linear-gradient(to right, var(--primary-solid) ${((answers[activeQuestion.id] ?? 3) - 1) * 25}%, rgba(255,255,255,0.1) ${((answers[activeQuestion.id] ?? 3) - 1) * 25}%)`
                    }}
                  />
                  <div className="flex justify-between mt-6">
                    <span className="text-sm font-medium text-gray-400 w-1/3 text-left leading-tight">{activeQuestion.left_label}</span>
                    <span className="text-xs font-mono text-primary/50 w-1/3 text-center pt-1">{answers[activeQuestion.id] ?? 3}</span>
                    <span className="text-sm font-medium text-gray-400 w-1/3 text-right leading-tight">{activeQuestion.right_label}</span>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
          </AnimatePresence>

          {/* Navigation */}
          {!loading && !loadError && (
            <div className="flex justify-between items-center">
              <button
                onClick={() => setCurrentIndex((idx) => Math.max(idx - 1, 0))}
                disabled={currentIndex === 0}
                className="px-6 py-3 rounded-full border border-white/40 bg-transparent text-gray-400 font-medium hover:bg-white/5 hover:text-white transition-all disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <span className="material-symbols-outlined text-sm">arrow_back</span>
                Back
              </button>
              {currentIndex < totalCount - 1 ? (
                <button
                  onClick={() => setCurrentIndex((idx) => Math.min(idx + 1, totalCount - 1))}
                  className="px-8 py-3 rounded-full bg-white text-black font-bold hover:bg-gray-200 transition-all flex items-center gap-2 shadow-[0_0_15px_rgba(255,255,255,0.2)]"
                >
                  Next
                  <span className="material-symbols-outlined text-sm">arrow_forward</span>
                </button>
              ) : (
                <button
                  onClick={() => void submitAssessment()}
                  disabled={!hasAllAnswers || submitting}
                  className="px-8 py-3 rounded-full bg-primary hover:bg-[#aacc00] text-black font-bold transition-all flex items-center gap-2 shadow-[0_0_20px_rgba(204,255,0,0.4)] disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? "Saving..." : "Submit Assessment"}
                  {!submitting && <span className="material-symbols-outlined text-sm">check_circle</span>}
                </button>
              )}
            </div>
          )}
        </div>

        {/* RIGHT: Dimension tracker */}
        <motion.div variants={stagger} initial="hidden" animate="visible" className="lg:col-span-5 flex flex-col gap-4">
          <div className="glass-panel rounded-none p-6 flex flex-col gap-1">
            <h3 className="text-xs font-mono text-gray-500 uppercase tracking-widest mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-[16px] text-primary">radar</span>
              Dimension Progress
            </h3>
            {Object.entries(QUESTION_DIMENSION).map(([qId, dim], idx) => {
              const answered = answers[qId] !== undefined;
              const active = questions[currentIndex]?.id === qId;
              return (
                <button
                  key={qId}
                  onClick={() => setCurrentIndex(idx)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-left ${
                    active
                      ? "bg-primary/10 border border-primary/30"
                      : "hover:bg-white/5 border border-transparent"
                  }`}
                >
                  <div className={`w-5 h-5 rounded-full flex-shrink-0 flex items-center justify-center text-[10px] font-bold border ${
                    answered
                      ? "bg-primary/20 border-primary/50 text-primary"
                      : "bg-white/5 border-white/10 text-gray-600"
                  }`}>
                    {answered
                      ? <span className="material-symbols-outlined text-[12px]">check</span>
                      : <span className="font-mono">{idx + 1}</span>
                    }
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-xs font-semibold truncate ${active ? "text-primary" : answered ? "text-gray-300" : "text-gray-600"}`}>
                      {dim.label}
                    </p>
                    <p className="text-[10px] text-gray-600 truncate">{dim.description}</p>
                  </div>
                  <span className={`text-[10px] font-mono flex-shrink-0 ${answered ? "text-primary" : "text-gray-700"}`}>
                    {answered ? `${dim.weight}pt` : "—"}
                  </span>
                </button>
              );
            })}
          </div>

          <motion.div variants={fadeInUp} className="glass-panel rounded-none p-5 border border-white/5">
            <p className="text-xs text-gray-500 leading-relaxed">
              <span className="text-white font-semibold">How scoring works:</span> Each dimension has a maximum weight (1–8pt). Higher-weight dimensions influence compatibility scores more. Answer all 8 to unlock team analysis.
            </p>
          </motion.div>
        </motion.div>

      </div>
    </motion.main>
  );
}

export function AssessmentClient() {
  return (
    <ErrorBoundary fallbackMessage="Assessment failed to load">
      <AssessmentInner />
    </ErrorBoundary>
  );
}
