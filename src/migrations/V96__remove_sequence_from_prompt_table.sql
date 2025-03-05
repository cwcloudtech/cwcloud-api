ALTER TABLE prompt DROP CONSTRAINT IF EXISTS unique_prompt_sequence;

DROP INDEX IF EXISTS idx_prompt_sequence;

ALTER TABLE prompt DROP COLUMN IF EXISTS sequence;
