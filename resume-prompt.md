# GitSyntropy — Resume Prompt (Next Session)

## Context
Project: GitSyntropy — team compatibility platform (FastAPI backend + Astro/React frontend).
All 10 backend features are complete. We are mid-way through a UX overhaul of the 6 frontend pages.
Design system: Tailwind CSS, neon lime primary (#ccff00), terminal/brutalist aesthetic.
Frontend: `apps/frontend/src/components/`, pages: `apps/frontend/src/pages/`.

## Completed This Session
- **InsightsClient.tsx** — fully rewritten:
  - `parseNarrative(text)` splits Claude markdown into `MdSection[]` (heading + bullets + paragraphs)
  - `Inline` component renders `**bold**` as `<strong>`
  - `NarrativeCard` renders sections with icons, expandable "Show N More Sections"
  - Idle state shows 4 pipeline explanation cards
  - "Analysing as: {userId}" context pill added
  - "Next Steps" sidebar replaces "Export Findings"
  - Report saved to localStorage and linked in header

## Remaining Tasks (in priority order)

### 1. DashboardClient.tsx
File: `apps/frontend/src/components/DashboardClient.tsx`

Changes needed:
- **User context pill**: In the `<header>` div, after the health status `<div className="flex items-center gap-2">` block (line ~306), add:
  ```tsx
  <span className="text-xs font-mono text-gray-500 bg-white/5 border border-white/10 px-2 py-0.5 rounded">
    You: {userId}
  </span>
  ```
- **GitHub Sync subtitle**: Below the `<h3>GitHub Sync</h3>` heading, before the input div, add:
  ```tsx
  <p className="text-xs text-gray-500 mt-1 mb-2">Enter a team member's GitHub username to analyse their commit patterns and chronotype.</p>
  ```
- **Empty team state**: After the team selector conditional in the header (line ~343), add:
  ```tsx
  {teams.length === 0 && !teamsLoading && (
    <div className="mt-3 p-3 border border-dashed border-white/20 rounded text-xs text-gray-500">
      No teams yet —{" "}
      <a href="/workspace" className="text-primary hover:text-white transition-colors">create your first team in Workspace →</a>
    </div>
  )}
  ```
- **Summary strip improvement**: All `.replace(/#{1,6}\s/g, "")` calls (lines ~452 and ~705) should also strip bullet `-` prefixes. Replace with:
  `.replace(/#{1,6}\s[^\n]*/g, "").replace(/\*\*/g, "").replace(/^- /gm, "").replace(/\n+/g, " ")`

### 2. AssessmentClient.tsx
File: `apps/frontend/src/components/AssessmentClient.tsx`

Changes needed:
- **Add question-to-dimension map** after the DIMENSION_CONFIG constant:
  ```tsx
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
  ```
- **"Profiling: {userId}" pill**: In the header section (the `<div className="w-full mb-8">` block), add below `<h1>Behavioral Assessment</h1>`:
  ```tsx
  <p className="text-xs font-mono text-gray-500 mt-1">Profiling: <span className="text-primary">{userId}</span></p>
  ```
- **Dimension description below question**: In the active question card, after the `<h2>` showing `{activeQuestion.prompt}` (line ~278), add:
  ```tsx
  {QUESTION_DIMENSION[activeQuestion.id] && (
    <p className="text-sm text-gray-500 -mt-8 mb-10 leading-relaxed">
      <span className="font-semibold text-gray-400">{QUESTION_DIMENSION[activeQuestion.id].label}</span>
      {" — "}{QUESTION_DIMENSION[activeQuestion.id].description}
    </p>
  )}
  ```

### 3. CompatibilityClient.tsx
File: `apps/frontend/src/components/CompatibilityClient.tsx`

Changes needed:
- **Input placeholders**: Member A input add `placeholder="e.g. alice, 1mystic"`, Member B add `placeholder="e.g. bob, dev_user"`.
- **Explanatory note below form**: After the `{error && ...}` line inside the glass panel, add:
  ```tsx
  <p className="text-xs text-gray-600 mt-4">
    Enter user IDs or GitHub handles of any two team members. Use "Full Data" for real assessment scores, or "Incomplete (Mock)" to test with simulated data.
  </p>
  ```
- **Post-result CTA block**: After the closing `</div>` of the `{data && (...)}` grid block, add a second `{data && (...)}` block:
  ```tsx
  {data && (
    <div className="mt-10 glass-panel rounded-none p-6 border border-primary/20 flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
      <div>
        <p className="text-sm font-semibold text-white mb-1">Ready to go deeper?</p>
        <p className="text-xs text-gray-400">Run a full multi-agent team analysis or view all pairings in the dashboard.</p>
      </div>
      <div className="flex gap-3 flex-shrink-0">
        <a href="/workspace" className="btn btn-primary text-xs px-4 py-2 flex items-center gap-1">
          <span className="material-symbols-outlined text-sm">schema</span>
          Full Team Analysis
        </a>
        <a href="/dashboard" className="btn btn-secondary text-xs px-4 py-2 flex items-center gap-1">
          <span className="material-symbols-outlined text-sm">dashboard</span>
          Dashboard
        </a>
      </div>
    </div>
  )}
  ```

### 4. WorkspaceClient.tsx
File: `apps/frontend/src/components/WorkspaceClient.tsx`

Changes needed:
- **Rename "Simulation Config" → "Team Setup"**: Line ~516: `<h2 ...>Simulation Config</h2>` → `Team Setup`
- **Add subtitle below "Team Setup" heading**: Add `<p className="text-xs text-gray-600 mt-1">Select a team and run a full multi-agent analysis — GitHub signals, psychometrics, and Claude synthesis.</p>`
- **Rename "Run Simulation" → "Run Full Analysis"**: Line ~624 button text
- **Wizard Step 3 text**: "Ready for simulation" → "Ready for full analysis" (line ~407)

### 5. Landing page (index.astro)
File: `apps/frontend/src/pages/index.astro`

After the bento grid section, add a "Navigate the Platform" section with 5 linked cards (icons from Material Symbols Outlined):
- **Dashboard** → /dashboard — icon: `dashboard` — "Run multi-agent team analysis and view compatibility scores"
- **Assessment** → /assessment — icon: `psychology` — "Complete your 8-dimension psychometric profile"
- **Compatibility** → /compatibility — icon: `compare_arrows` — "Compute pairwise Ashtakoot compatibility scores"
- **Workspace** → /workspace — icon: `schema` — "Create teams, invite members, run full synthesis"
- **Insights** → /insights — icon: `auto_awesome` — "Read your AI-generated team narrative report"

### 6. Create /guide.astro
File: `apps/frontend/src/pages/guide.astro`

Full documentation/onboarding page with these sections:
1. **Getting Started** — 3-step flow: complete assessment → create team + sync GitHub → run analysis
2. **Assessment** — 8 dimensions, weights, how scores feed into compatibility
3. **GitHub Sync** — what data is fetched, what chronotype means
4. **Compatibility Engine** — Ashtakoot 8-dimension framework, scoring out of 36
5. **Team Analysis Pipeline** — LangGraph 4-step pipeline (github_analyst → psychometric_profiler → compatibility_engine → synthesis)
6. **Insights Report** — how to read the narrative, what sections mean

Use same layout pattern as other pages (check `Nav.astro` for nav component import). Add "Guide" link to nav.

---

## Key Technical Notes
- `userId` = `session?.userId ?? AUTH_BYPASS_USER_ID` (from `$session.get()` in nanostores, already available in all components)
- Auth is dev-bypass mode by default; `AUTH_REQUIRED` is false
- Dimension weight order (backend): varna=1, vashya=2, tara=3, yoni=4, graha_maitri=5, gana=6, bhakoot=7, nadi=8
- Question IDs q1→varna (weight 1) through q8→nadi (weight 8)
- The nav component is at `apps/frontend/src/components/Nav.astro`
- InsightsClient.tsx was just rewritten — do NOT touch it unless fixing a bug
- Git status: CompatibilityClient.tsx and WorkspaceClient.tsx both show as modified (M) from previous session

## Memory Location
`C:\Users\athar\.claude\projects\g--synced-pc-1-Work-projects-GitSyntropy\memory\`



<old>
"""
Update Todos

Fix InsightsClient: render markdown narrative as sections not raw text

Fix DashboardClient: user context, better labels, empty states, onboarding

Fix CompatibilityClient: context placeholders, CTA after results

Fix AssessmentClient: user context + dimension description

Fix WorkspaceClient: rename labels, add descriptions, clarify purpose

Update landing page: add Platform Guide navigation section

Create /guide.astro documentation page


Now I have enough to plan all the changes. Let me prioritize:

InsightsClient.tsx — Fix markdown rendering (biggest visual bug from screenshots)

DashboardClient.tsx — Add user context, better labels, onboarding empty state

CompatibilityClient.tsx — Add context placeholders + CTA

AssessmentClient.tsx — Add user context indicator

WorkspaceClient.tsx — Fix "SIMULATION CONFIG" label, better descriptions

Landing page (index.astro) — Add "How to use" navigation cards section

Create /docs.astro — Documentation page

Starting with the most impactful changes. For InsightsClient, I need to handle the markdown in data.narrative properly — parsing headers into <h3> tags, bold text into <strong>, and bullet points into list items, then displaying them as cards with a "View Full Report" button to truncate longer content. I'll create a helper function to handle this rendering.

For DashboardClient, I'm adding user context information and improving the empty state messaging for onboarding.

For CompatibilityClient, I need to add clearer instructions and example placeholders so users understand they can search by username or GitHub handle, plus a call-to-action linking to the full team analysis.

For AssessmentClient, I'm showing which user is completing the assessment and adding dimension descriptions pulled from the config below each question.

For WorkspaceClient, I'm renaming the header from "SIMULATION CONFIG" to "TEAM SETUP" and refining the snapshot labels for better clarity.

I'm also planning a landing page navigation section with cards for each feature and a new guide page with documentation for all the tools.

Now I'm building a markdown renderer utility that parses section headings, bold text, and bullet points...

Writing markdown parser... I'm realizing the markdown parsing is getting too complicated, so I'll take a simpler approach instead—strip out the markdown formatting for a clean preview and let users click through to see the full formatted report where react-markdown can handle all the styling properly. For the Insights display, I'll show a compact summary of the first couple sentences, pull out key highlights as cards, keep the recommendations as they are, and add a button to view the complete report. Finishing the parser function and then considering whether to use react-markdown if it's already available in the project. Now I'm mapping out the specific UI updates needed across all the client components. I need to update DashboardClient to show the user ID and improve the GitHub sync instructions, add empty states to assessment and compatibility sections, then refine AssessmentClient with dimension descriptions and update the workspace labels from "SIMULATION" to "TEAM SETUP" with better explanatory text.

After that, I'll add a Platform Guide section to the landing page and create a dedicated guide documentation page to tie everything together.


DashboardClient.tsx changes:

Add "You are: {userId}" pill in header, after system status
GitHub Sync card subtitle
Empty team state message
Fix summary strip to also remove bullet - prefixes
AssessmentClient.tsx changes:

Add "Profiling: {userId}" in header

Show dimension description text below question prompt by mapping the question ID to its dimension key

CompatibilityClient.tsx changes:

Input placeholders with examples
Add explanatory note below form
Add post-result CTA
WorkspaceClient.tsx changes:

"Simulation Config" → "Team Setup"
"Run Simulation" → "Run Full Analysis"
"Ready for simulation" → "Ready for full analysis"
"""
</old>