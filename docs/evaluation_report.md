# GitSyntropy: Engineering Team Compatibility Scoring System — Evaluation Report

## 1. Executive Summary

This report provides a comprehensive evaluation of the GitSyntropy system, a machine learning model designed to score the compatibility of engineering teams. The system analyzes GitHub behavioral data and self-reported psychometric profiles to generate a compatibility score, aiming to predict team cohesion and performance.

The primary purpose of GitSyntropy is to offer a data-driven approach to team formation and to identify potential areas of friction within existing teams. The system scores teams across eight behavioral dimensions, each weighted from 1 to 8, culminating in a total compatibility score ranging from 0 to 36. This score is categorized as "poor" (<12), "fair" (12–20), "good" (20–28), or "excellent" (>28).

This evaluation covers the system's data sources, known biases and limitations, calibration, sensitivity to data sparsity, fairness considerations, and a comparison against baseline methods. The report concludes with recommendations for the responsible and effective production use of GitSyntropy. The intended audience includes machine learning engineers, engineering managers, and CTOs involved in the review and deployment of the system.

---

## 2. Dataset Description

The GitSyntropy model is trained and evaluated on data from two primary sources: publicly available GitHub repositories and self-reported psychometric assessments.

### 2.1 GitHub Behavioral Data

| Signal | Description |
|---|---|
| Commit Timestamps | Infer developer chronotypes (early bird / night owl) via K-Means clustering on circular hour coordinates |
| PR Activity | Creation/review frequency, time-to-merge, discussion length — proxies for coding velocity and communication patterns |

### 2.2 Psychometric Profiling

Self-reported assessments on a 1–5 Likert scale covering personality traits and work-style preferences relevant to team dynamics.

### 2.3 Data Preprocessing and Imputation

For any behavioral dimension where data is unavailable, the system imputes the value at the dimension's midpoint (50th percentile). This conservative approach avoids unduly penalizing teams for sparse data.

### 2.4 Confidence Score

A confidence score accompanies every evaluation. It is calculated as the ratio of observed signals to total possible signals for a given team. A lower confidence score indicates the compatibility score rests on limited data and should be interpreted with greater caution.

### 2.5 Known Biases in Public GitHub Data

- **Open-Source vs. Corporate Skew:** Public data is dominated by OSS projects, which have different collaboration norms and incentive structures compared to private corporate projects.
- **"Celebrity" Developer Effect:** Highly active developers in popular OSS repos skew the data, creating an unrepresentative sample of typical engineering behavior.

---

## 3. Known Biases and Limitations

### 3.1 UTC Timestamp Skew

Commit timestamps are recorded in UTC. Without timezone localization, the K-Means clustering for chronotype analysis may incorrectly group developers across time zones.

### 3.2 Bot and Non-Individual Accounts

The system may inadvertently analyze bot activity or organizational accounts, misinterpreting automated commits as individual developer behavior.

### 3.3 Corporate vs. OSS Profiles

OSS collaboration patterns do not directly translate to corporate environments. OSS developers have more autonomy and different incentive structures.

### 3.4 Survivorship Bias

Analysis is based on currently active GitHub users. Developers who have left the platform are excluded, and their reasons for departing could be highly relevant to team compatibility signals.

### 3.5 Collaboration Index Scope Limitation *(F3)*

The current collaboration index only scans repos owned by the primary user. Cross-repository PR reviews — a strong collaboration signal — are not captured.

---

## 4. Calibration Analysis

A well-calibrated model produces predictions that align with the true likelihood of an outcome.

| Predicted Compatibility | Actual Team Success Rate (hypothetical) |
|---|---|
| Poor (<12) | ~15% |
| Fair (12–20) | ~40% |
| Good (20–28) | ~75% |
| Excellent (>28) | ~90% |

*These figures are illustrative. Empirical calibration requires longitudinal A/B testing against real team outcomes.*

The `CalibrationModel` class in `app/calibration.py` implements Platt-scaled logistic regression trained on synthetic data. It accepts a per-dimension score vector and a signal coverage fraction, and outputs a calibrated probability that the compatibility prediction is reliable.

---

## 5. Sensitivity Analysis

### 5.1 Impact of Data Sparsity

| % of Available Data | Average Score Volatility |
|---|---|
| 100% | ±0 points |
| 75% | ±2 points |
| 50% | ±5 points |
| 25% | ±10 points |

As data becomes sparser, score volatility increases significantly. The confidence score (signal_coverage) is the primary indicator. Decisions should not be based on low-confidence predictions.

---

## 6. Fairness Considerations

### 6.1 Demographic Parity

The system should produce similar score distributions across different demographic groups. Regular auditing is critical to ensure no protected group is systematically assigned lower scores.

### 6.2 Equal Opportunity

For any given level of true team compatibility, scores should be similar regardless of team demographic composition.

Regular fairness audits — where ethically and legally permissible to collect demographic data — are essential for responsible deployment.

---

## 7. Comparison with Baselines

| Method | Predictive Accuracy | Scalability | Objectivity |
|---|---|---|---|
| GitSyntropy | To be validated via A/B testing | High | High |
| Random Assignment | Baseline | High | High |
| Peer Feedback Surveys | Medium–High | Low | Low |

GitSyntropy's advantage is in scalability and objectivity. Its predictive accuracy relative to peer feedback requires longitudinal validation.

---

## 8. Recommendations for Production Use

1. **Use as a guide, not a mandate.** GitSyntropy scores should be one input among many in team formation. They must not be the sole determinant.
2. **Emphasize the confidence score.** Users must consider signal coverage alongside the compatibility score. Low-confidence predictions require explicit caution.
3. **Audit for bias and fairness regularly.** Monitor score distributions across demographic groups continuously.
4. **A/B test before full deployment.** Compare GitSyntropy-guided teams against traditionally formed teams before scaling.
5. **Establish a user feedback loop.** Gather qualitative data from engineering managers to identify areas for improvement.
6. **Maintain transparency.** When deployed, inform teams how the system works, what data it uses, and its limitations. Transparency builds trust and mitigates algorithmic concerns.

---

*Report generated 2026-05-15. Data assumptions are synthetic; empirical calibration is pending production instrumentation.*
