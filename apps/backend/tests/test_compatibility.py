from app.services import compatibility, mock_compatibility_scores


def test_compatibility_full_data_contract() -> None:
    payload = compatibility(
        mock_compatibility_scores("alice", data_mode="full"),
        mock_compatibility_scores("bob", data_mode="full"),
    )

    assert payload["total_score_36"] <= 36
    assert payload["score_pct_100"] <= 100
    assert payload["confidence"] == 1.0
    assert payload["insufficient_confidence"] is False
    assert payload["uncertainty_band"] == "low"
    assert len(payload["dimension_breakdown"]) == 8
    assert set(payload["dimension_scores"]) == {
        "varna_alignment",
        "vashya_influence",
        "tara_resilience",
        "yoni_workstyle",
        "graha_maitri_cognition",
        "gana_temperament",
        "bhakoot_strategy",
        "nadi_chronotype_sync",
    }


def test_compatibility_incomplete_data_flags_risk() -> None:
    payload = compatibility(
        mock_compatibility_scores("night-architect", data_mode="incomplete"),
        mock_compatibility_scores("early-ops", data_mode="incomplete"),
    )

    assert payload["confidence"] < 1.0
    assert len(payload["data_gaps"]) >= 1
    assert any("Low confidence" in flag for flag in payload["risk_flags"])
    assert payload["uncertainty_band"] in {"moderate", "high"}
