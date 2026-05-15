# Production Targets (Near-Production Readiness)

## Model Quality

- Predictive validity: ROC-AUC >= 0.75 on held-out public OSS benchmark splits
- Calibration: Expected Calibration Error (ECE) <= 0.05
- Robustness: <= 10% degradation under missingness/noise stress tests
- Uncertainty: abstain/insufficient-confidence rate explicitly tracked and surfaced

## Data Quality

- Missing critical feature columns: 0 tolerated in feature-ready snapshots
- Timestamp anomaly rate: < 2% of samples per refresh window
- Bot-account contamination: tracked and filtered with explicit confidence flags
- Lineage completeness: 100% of training runs linked to dataset + feature snapshot IDs

## Reliability + Performance

- API p95 latency: <= 400ms for scoring endpoints (excluding LLM synthesis)
- WebSocket stream startup p95: <= 1.5s
- Availability target: >= 99.5% (monthly)
- Run failure recovery: idempotent retries and structured error events for all orchestrator nodes

## Security + Governance

- OAuth state validation: required on callback
- Security headers enabled on all HTTP responses
- Public-data-only policy enforced and documented
- Responsible-use messaging shown in docs and UI for non-hiring scope
