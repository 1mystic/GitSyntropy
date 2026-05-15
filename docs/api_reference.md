# GitSyntropy API Reference

Base URL: `https://<railway-url>/api/v1`

All endpoints that require authentication expect a `Bearer <jwt>` token in the `Authorization` header.

---

## System

| Method | Endpoint | Description | Auth | Key Request Fields | Key Response Fields | Common Errors |
|---|---|---|---|---|---|---|
| `GET` | `/health` | Health check — confirms API availability and deployment version. Used by load balancers and Railway health probes. | None | — | `status`, `service`, `version` | `500`, `503` |

---

## Authentication

| Method | Endpoint | Description | Auth | Key Request Fields | Key Response Fields | Common Errors |
|---|---|---|---|---|---|---|
| `POST` | `/auth/github/start` | Initiates GitHub OAuth 2.0 flow. Returns the authorization URL to redirect the browser to. | None | `redirect_uri` (opt) | `auth_url`, `state` | `400`, `500` |
| `POST` | `/auth/github/callback` | Completes GitHub OAuth by exchanging the temporary code for a JWT. | None | `code`, `state` | `access_token`, `token_type`, `expires_in` | `400`, `401`, `502` |
| `POST` | `/auth/login` | Dev-only fallback login (not secure for production). | None | `github_handle` | `access_token`, `expires_in` | `400`, `404` |
| `GET` | `/auth/session` | Validates the JWT in the Authorization header and returns session metadata. | Bearer JWT | — | `is_valid`, `user_id`, `expires_at` | `401`, `403` |

---

## Users

| Method | Endpoint | Description | Auth | Key Request Fields | Key Response Fields | Common Errors |
|---|---|---|---|---|---|---|
| `GET` | `/users/me` | Returns the full profile of the currently authenticated user. | Bearer JWT | — | `id`, `handle`, `name`, `role`, `created_at` | `401`, `404` |
| `GET` | `/users/search` | Searches the user directory by partial name or GitHub handle. Rate-limited: 30 req/min. | Bearer JWT | `q`, `limit`, `offset` | `results`, `total_count`, `next_page` | `400`, `401`, `422`, `429` |
| `PATCH` | `/users/me/display-name` | Updates the authenticated user's display name. | Bearer JWT | `display_name` | `id`, `display_name` | `401`, `422` |

---

## Admin

| Method | Endpoint | Description | Auth | Key Request Fields | Key Response Fields | Common Errors |
|---|---|---|---|---|---|---|
| `GET` | `/admin/stats` | Returns aggregate platform statistics. Superadmin only. | Bearer JWT (superadmin) | — | `user_count`, `team_count`, `run_count` | `401`, `403` |
| `GET` | `/admin/users` | Paginated list of all platform users. Superadmin only. | Bearer JWT (superadmin) | `limit`, `offset` | `users`, `total` | `401`, `403` |

---

## GitHub

| Method | Endpoint | Description | Auth | Key Request Fields | Key Response Fields | Common Errors |
|---|---|---|---|---|---|---|
| `POST` | `/github/sync` | Triggers an async background job to ingest the authenticated user's latest GitHub data. `user_id` in request body is ignored — identity is derived from JWT. | Bearer JWT | *(none required — user_id from JWT)* | `job_id`, `status`, `estimated_eta` | `401`, `403`, `404`, `429` |
| `GET` | `/github/sync/{id}` | Returns the status of a previously triggered GitHub sync job. | Bearer JWT | — | `id`, `status`, `github_handle`, `chronotype` | `401`, `404` |

---

## Assessment

| Method | Endpoint | Description | Auth | Key Request Fields | Key Response Fields | Common Errors |
|---|---|---|---|---|---|---|
| `GET` | `/assessment/questions` | Returns the 8 psychometric questions, each mapped to a behavioral dimension. | Bearer JWT | — | `questions[]` (id, text, dimension, scale) | `401`, `500` |
| `GET` | `/assessment/responses/{user_id}` | Returns stored assessment responses for a user. | Bearer JWT | — | `responses[]`, `completed` | `401`, `404` |
| `POST` | `/assessment/responses` | Submits assessment answers. `user_id` in body is ignored — identity from JWT. | Bearer JWT | `responses[]` (id/score pairs) | `assessment_id`, `status`, `score_summary` | `400`, `401`, `422` |
| `POST` | `/assessment/submit` | Duplicate of `/assessment/responses` — to be removed (issue O3). | Bearer JWT | `responses[]` | same as above | `400`, `401`, `422` |
| `POST` | `/assessment/cat/next` | Returns the next optimal question in a CAT session using IRT 3PL Fisher Information maximization. Stops when SE < 0.35 or all 8 questions answered. | Bearer JWT | `current_answers` (dict qid→int 1–5) | `next_question_id`, `estimated_theta`, `se_theta`, `rationale` | `400`, `401`, `422` |

---

## Teams

> **Note:** All team endpoints require Bearer JWT authentication. `user_id` in request bodies is ignored — identity is derived from the JWT.

| Method | Endpoint | Description | Auth | Key Request Fields | Key Response Fields | Common Errors |
|---|---|---|---|---|---|---|
| `POST` | `/teams` | Creates a new team. `created_by` is set to the authenticated user. | Bearer JWT | `name`, `description` | `team_id`, `name`, `created_by`, `created_at` | `400`, `401`, `409` |
| `GET` | `/teams` | Lists all teams visible to the authenticated user. | Bearer JWT | `limit`, `offset` | `teams[]`, `total_count` | `401`, `500` |
| `GET` | `/teams/{id}` | Returns full details for a specific team including members. | Bearer JWT | — | `id`, `name`, `members[]` | `401`, `404` |
| `PATCH` | `/teams/{id}` | Updates team metadata. | Bearer JWT | `name`, `description` | updated team object | `401`, `403`, `404` |
| `POST` | `/teams/{id}/members` | Adds a user to the team. | Bearer JWT | `user_id` | `team_id`, `user_id`, `joined_at` | `400`, `401`, `403`, `404` |
| `DELETE` | `/teams/{id}/members/{user_id}` | Removes a member from the team. | Bearer JWT | — | `status` | `401`, `403`, `404` |

---

## Analysis

| Method | Endpoint | Description | Auth | Key Request Fields | Key Response Fields | Common Errors |
|---|---|---|---|---|---|---|
| `POST` | `/compatibility/run` | Runs pairwise compatibility scoring between two dimension-score maps. | Bearer JWT | `member_a` (dim→score), `member_b` | `total_score_36`, `category`, `dimension_breakdown`, `confidence` | `400`, `401`, `422` |
| `POST` | `/orchestrator/run` | Triggers the full LangGraph pipeline: GitHub sync → psychometric profiler → compatibility engine → Claude synthesis. Returns a `run_id` for WebSocket streaming. | Bearer JWT | `team_id`, `user_id` (ignored — from JWT), `include_candidates` | `run_id`, `status` | `401`, `403`, `503` |
| `POST` | `/candidates/simulate` | Monte Carlo simulation: evaluates how a candidate would impact a team's compatibility. Seed is derived deterministically from team scores. | Bearer JWT | `team_id`, `n_iterations` | `n_iterations`, `optimal_profile`, `mean_improvement`, `weak_dimensions_targeted` | `400`, `401`, `404` |
| `GET` | `/insights/synthesis` | Returns the latest cached synthesis report for a user. | Bearer JWT | `user_id` (query param) | `synthesis_text`, `run_id`, `score_category` | `400`, `401`, `404` |

---

## WebSocket

| Protocol | Endpoint | Description |
|---|---|---|
| WebSocket | `/ws/analysis/{run_id}` | Streams LangGraph pipeline events in real-time. Each message is a JSON object with `type`, `step`, `status`, and `data` fields. The final event has `type: "complete"`. |

### WebSocket Event Types

| `type` | Description |
|---|---|
| `pipeline_step` | Emitted when a LangGraph node completes. `step` identifies which node. |
| `synthesis_chunk` | Streaming text chunk from Claude synthesis (batched, not character-by-character). |
| `complete` | Pipeline finished. |
| `error` | Pipeline error with message. |

---

*Last updated: 2026-05-15*
