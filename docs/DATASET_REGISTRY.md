# Public Dataset Registry

| Dataset | Source | License / Terms | Schema Focus | Refresh Cadence | Known Biases |
|---|---|---|---|---|---|
| GH Archive (GitHub Events) | https://www.gharchive.org/ | Public event archive (check GitHub Terms) | event_type, actor/repo metadata, timestamps | Daily | UTC-heavy timestamps, bot activity, public-repo skew |
| Public GitHub metadata snapshots (Perceval/GHTorrent-derived) | Public mirrors / derived dumps | Varies by source mirror | PR/issue/comment/commit metadata | Snapshot-based | Missing private collaboration, survivorship bias |
| Stack Overflow public data | Stack Exchange Data Dump/API | CC BY-SA (with attribution requirements) | tags, activity patterns, Q/A behavior | Periodic dump + API polling | Language/community skew, reputation dynamics |
| Public OSS issue/PR benchmark datasets | Research repos and open benchmarks | Varies by dataset | review latency, merge outcomes, churn proxies | Per release | Project-selection bias, label quality variance |

## Registry Rules

- Only legally reusable, publicly available data can enter raw ingestion.
- Every dataset must record license terms, intended use, and attribution requirements.
- Every transformed table must track source dataset IDs + snapshot timestamp.
- Bias notes are mandatory and must be visible to model consumers.
