# GitSyntropy — External LLM Prompt Templates

> Copy-paste these into the respective AI tool. Each prompt is self-contained.
> After getting output, paste the result back to Claude Code with: "Integrate this into the project at [file]."

---

## GPT-4 / ChatGPT Prompts

---

### [P3-1] IRT-Based CAT Question Selection

**Paste this into GPT-4 (use GPT-4o for best math quality):**

```
I'm building a Computerized Adaptive Testing (CAT) system for a psychometric assessment tool.

The assessment has 8 questions (q1–q8), each measuring one behavioral dimension with a max weight (q1=1pt, q2=2pt, ..., q8=8pt).

Current (wrong) implementation: just picks questions from highest to lowest weight.

I need: A proper IRT-based (3PL model) CAT implementation in Python.

Requirements:
1. Use the 3-parameter logistic IRT model: P(θ|a,b,c) = c + (1-c) / (1 + exp(-a*(θ-b)))
2. After each answer (on a 1-5 scale), update θ using EAP (Expected A Posteriori) estimation
3. Select the next question that maximizes Fisher information at current θ: I(θ) = (a² * (P(θ)-c)²) / ((1-c)² * P(θ) * (1-P(θ)))
4. Stop when SE(θ) < 0.35 or all questions answered
5. Return: next_question_id (str or None), estimated_theta (float), se_theta (float), rationale (str)

Provide default IRT parameters (a, b, c) for each of the 8 questions — calibrate them so:
- q8 (Chronotype Sync, weight 8) is the hardest and most discriminating
- q1 (Innovation Drive, weight 1) is easiest and least discriminating
- Guessing parameter c should be near 0 (Likert scale, not multiple choice)

Implement these two functions:
- cat_select_next_question(current_answers: dict[str, int]) -> str | None
- cat_estimated_theta(current_answers: dict[str, int]) -> dict (theta, se, rationale)

The answers dict maps question id to int 1–5.
Return clean Python code only, no explanations.
```

---

### [P0-3] Fernet Token Encryption Helper

**Paste this into GPT-4:**

```
Write a Python encryption/decryption helper for storing GitHub OAuth access tokens in a PostgreSQL database using the cryptography library's Fernet symmetric encryption.

Requirements:
1. Key derivation: Use PBKDF2HMAC(SHA256) to derive a 32-byte key from an environment variable (GS_JWT_SECRET as bytes) + a fixed salt ("gitsyntropy-token-encryption").
2. Functions needed:
   - encrypt_token(token: str, secret: str) -> str (returns base64url-safe encrypted string)
   - decrypt_token(encrypted: str, secret: str) -> str (returns plaintext token)
   - Both should handle None gracefully (return None if input is None)
3. The encrypted result must be storable as a Text column in PostgreSQL.
4. Thread-safe, no global state.

Return only the Python module code. No external dependencies beyond `cryptography`.
```

---

### [P3-2] Platt Scaling Calibration

**Paste this into GPT-4:**

```
I have a compatibility scoring model that outputs a "confidence" value (0-1 float) representing how reliable the team compatibility score is. Currently confidence is just: observed_signals / total_signals — a naive coverage ratio.

I need to implement Platt scaling to calibrate this confidence output so it reflects actual predictive accuracy.

Context:
- The model scores pairs of engineers on 8 behavioral dimensions
- Each dimension has a true score (from assessment) or imputed score (midpoint default)
- "Confidence" should reflect: given this score, what's the probability the team will actually perform at the predicted compatibility level?
- We don't have labeled ground-truth data yet, so use a synthetic calibration approach

Provide:
1. A CalibrationModel class that:
   - Takes (score_vector, signal_coverage) as input features
   - Returns calibrated_confidence (float 0-1)
   - Can be serialized to JSON for storage
   - Has a from_synthetic_data() class method that generates training data based on reasonable assumptions
2. A fit() method using sklearn's LogisticRegression (Platt scaling)
3. A calibration_plot_data() method returning arrays for a reliability diagram

Requirements: sklearn, numpy only. Return Python code only.
```

---

## Gemini Advanced Prompts

---

### [P3-3] Evaluation Report Generation

**Paste this into Gemini Advanced (use 1.5 Pro with long context):**

```
I'm building an ML system called GitSyntropy that scores engineering team compatibility from GitHub behavioral data and psychometric profiling.

Generate a comprehensive evaluation report template in Markdown format for this system. The report should be suitable for a technical audience (ML engineers, CTOs) reviewing the system.

System details:
- 8 behavioral dimensions scored 0-N (N = dimension weight 1-8)
- Total score 0-36: <12 poor, 12-20 fair, 20-28 good, >28 excellent
- Data sources: GitHub commit timestamps (chronotype via K-Means), PR activity, self-reported psychometric assessment (1-5 Likert scale)
- Missing data imputed at dimension midpoint (50%)
- Confidence = observed_signals / total_possible_signals

The evaluation report should include sections for:
1. Executive Summary (system purpose, evaluation scope)
2. Dataset Description (what data is used, known biases in public GitHub data)
3. Known Biases and Limitations (UTC timezone skew, bot accounts, corporate vs OSS profiles, survivorship bias)
4. Calibration Analysis (placeholder for actual calibration curves)
5. Sensitivity Analysis (how scores change under data sparsity)
6. Fairness Considerations (demographic parity, equal opportunity)
7. Comparison with Baselines (random assignment, peer feedback surveys)
8. Recommendations for Production Use

Include actual numbers where you can derive them from first principles. Use tables and headers. The report should be ~1500 words. Output Markdown only.
```

---

### [P6-5] OpenAPI Documentation Enhancement

**Paste this into Gemini Advanced:**

```
I have a FastAPI backend with these endpoints. Generate a comprehensive OpenAPI description for each endpoint — including description, request/response examples, error cases, and authentication requirements.

Endpoints (FastAPI):
- GET /api/v1/health → HealthResponse(status, service, version)
- POST /api/v1/auth/github/start → Returns OAuth redirect URL
- POST /api/v1/auth/github/callback → Exchanges code for JWT
- GET /api/v1/auth/session → Validates current JWT
- GET /api/v1/users/me → Authenticated user profile
- GET /api/v1/users/search?q=... → Search users by handle/name
- POST /api/v1/github/sync → Triggers GitHub data sync for a user
- GET /api/v1/assessment/questions → Returns 8 psychometric questions
- POST /api/v1/assessment/responses → Submits assessment answers
- POST /api/v1/assessment/cat/next → CAT next question selection
- POST /api/v1/compatibility/run → Runs pairwise compatibility scoring
- POST /api/v1/orchestrator/run → Starts multi-agent pipeline
- POST /api/v1/candidates/simulate → Monte Carlo hire simulation
- GET /api/v1/insights/synthesis → Get latest synthesis report
- POST /api/v1/teams → Create a team
- GET /api/v1/teams → List user's teams
- POST /api/v1/teams/{id}/members → Add team member

For each endpoint provide:
- 2-sentence description
- Auth requirement (None / Bearer JWT / Superadmin)
- Key request fields
- Key response fields
- Common error codes

Format as a Markdown table for each endpoint group (Auth, Users, GitHub, Assessment, Teams, Analysis). Output Markdown only.
```

---

## Qwen / OSS LLM Prompts

---

### [P3-5] Benchmark Dataset Generation

**Paste this into Qwen2.5-72B or similar:**

```
Generate a synthetic benchmark dataset for evaluating a team compatibility scoring system.

The dataset should contain 50 pairs of engineer profiles with:
1. Dimension scores (8 dimensions, each 0.0 to weight_max):
   - innovation_drive: 0.0–1.0
   - leadership_orientation: 0.0–2.0
   - team_resilience: 0.0–3.0
   - work_style: 0.0–4.0
   - decision_style: 0.0–5.0
   - risk_tolerance: 0.0–6.0
   - stress_response: 0.0–7.0
   - chronotype_sync: 0.0–8.0
2. A ground_truth_compatibility label: "excellent" | "good" | "fair" | "poor"
3. A rationale string explaining why that label applies

Make the dataset representative:
- 25% excellent pairs (complementary scores, similar chronotype)
- 35% good pairs (minor friction in 1-2 dimensions)
- 25% fair pairs (clear misalignment in high-weight dimensions)
- 15% poor pairs (multiple critical mismatches)

Output as a JSON array. Each element:
{
  "pair_id": "P001",
  "member_a": { "innovation_drive": 0.8, ... },
  "member_b": { "innovation_drive": 0.3, ... },
  "ground_truth": "good",
  "rationale": "..."
}

Output only the JSON array, no markdown wrapper.
```

---

### [P2-4] Monte Carlo with Proper Entropy

**Paste this into any capable model:**

```
I have a Python function that runs Monte Carlo simulation to find an optimal candidate profile for a software team:

def monte_carlo_candidate_simulation(team_scores: list[dict], n_iterations=1000) -> dict:
    rng = random.Random(42)  # BUG: fixed seed, always same result
    ...

Fix the seed to be deterministic per unique team configuration (so same team always gets same result, but different teams get different results), without using wall-clock time.

Requirements:
- Seed must be derived from the team_scores data structure
- Must be stable across runs (reproducible for same input)
- Must differ for different team compositions
- Use only Python stdlib (hashlib, json, random)

Provide just the corrected seed line (2-3 lines of code). No explanation.
```

---

## Claude Code Integration Prompts

After getting output from any of the above, paste this to Claude Code:

```
I got this code from [GPT-4/Gemini/Qwen] for task [task ID]:

[PASTE GENERATED CODE]

Please integrate it into the GitSyntropy project:
- Read CONTEXT.md first to understand the codebase
- File to modify: [file path]
- Ensure it follows the existing patterns (async, proper imports, no breaking changes)
- Update CONTEXT.md changelog after the change
```

---

## Session Start Template

Use this at the start of every new Claude Code session:

```
Read CONTEXT.md and PLAN.md in the GitSyntropy project root first.
Then continue from where the last session left off.
The next task is: [paste from PLAN.md]
```
