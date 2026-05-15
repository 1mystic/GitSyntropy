# Consent, Privacy, and Responsible Use Policy

## Scope

GitSyntropy is designed for OSS collaboration analysis using public signals.  
It is **not** intended for employment or hiring decisions.

## Data Constraints

- Use only public, legally reusable datasets and APIs.
- Do not ingest private repositories, private communication tools, or non-consensual private telemetry.
- Minimize profile-level storage and retain only fields required for modeling.

## Consent and Transparency

- Show explicit notice that profile-level inferences are being computed from public data.
- Provide users with clear uncertainty labels, data-gap indicators, and known limitations.
- Provide opt-out controls for local profile persistence where feasible.

## Model Output Guardrails

- Low-confidence outputs must be marked as inconclusive.
- Reports must include uncertainty and non-causal caveats.
- No output should present itself as deterministic truth about a person.

## Governance

- Document dataset provenance and licensing in `docs/DATASET_REGISTRY.md`.
- Track model versions, feature snapshots, and evaluation artifacts for auditability.
- Run periodic bias and drift checks before promoting model updates.
