-- Migration 0001: rename legacy (Ashtakoot-derived) dimension keys to neutral
-- psychometric terms in all stored JSONB columns.
--
-- Affected columns:
--   psychometric_profiles.scores            (JSONB object: key -> score)
--   team_scores.dimension_scores            (JSONB object: key -> score)
--   team_scores.weak_dimensions             (JSONB array of dimension strings)
--   team_scores.strong_dimensions           (JSONB array of dimension strings)
--
-- The legacy keys are globally-unique tokens, so a text-level replace over the
-- JSONB representation is safe and remaps both object keys and array values in
-- one pass. Idempotent: running it twice is a no-op (the old tokens are gone).
--
-- Apply on a Supabase branch first, verify, then promote. The application also
-- carries a read-time shim (schemas.normalize_dimension_keys) so unmigrated rows
-- never break; this migration makes the rename permanent so the shim can later
-- be removed.

BEGIN;

CREATE OR REPLACE FUNCTION _rename_dimension_keys(doc jsonb)
RETURNS jsonb AS $$
DECLARE
    t text;
BEGIN
    IF doc IS NULL THEN
        RETURN NULL;
    END IF;
    t := doc::text;
    t := replace(t, 'varna_alignment',        'innovation_drive');
    t := replace(t, 'vashya_influence',        'leadership_orientation');
    t := replace(t, 'tara_resilience',         'team_resilience');
    t := replace(t, 'yoni_workstyle',          'work_style');
    t := replace(t, 'graha_maitri_cognition',  'decision_style');
    t := replace(t, 'gana_temperament',        'risk_tolerance');
    t := replace(t, 'bhakoot_strategy',        'stress_response');
    t := replace(t, 'nadi_chronotype_sync',    'chronotype_sync');
    RETURN t::jsonb;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

UPDATE psychometric_profiles
SET scores = _rename_dimension_keys(scores)
WHERE scores::text ~ 'varna_alignment|vashya_influence|tara_resilience|yoni_workstyle|graha_maitri_cognition|gana_temperament|bhakoot_strategy|nadi_chronotype_sync';

UPDATE team_scores
SET dimension_scores  = _rename_dimension_keys(dimension_scores),
    weak_dimensions   = _rename_dimension_keys(weak_dimensions),
    strong_dimensions = _rename_dimension_keys(strong_dimensions)
WHERE (dimension_scores::text  ~ 'varna_alignment|vashya_influence|tara_resilience|yoni_workstyle|graha_maitri_cognition|gana_temperament|bhakoot_strategy|nadi_chronotype_sync')
   OR (weak_dimensions::text   ~ 'varna_alignment|vashya_influence|tara_resilience|yoni_workstyle|graha_maitri_cognition|gana_temperament|bhakoot_strategy|nadi_chronotype_sync')
   OR (strong_dimensions::text ~ 'varna_alignment|vashya_influence|tara_resilience|yoni_workstyle|graha_maitri_cognition|gana_temperament|bhakoot_strategy|nadi_chronotype_sync');

DROP FUNCTION _rename_dimension_keys(jsonb);

COMMIT;

-- Rollback note: there is no automatic down-migration. To revert, restore from a
-- pre-migration backup/branch, or run the inverse text replacements.
