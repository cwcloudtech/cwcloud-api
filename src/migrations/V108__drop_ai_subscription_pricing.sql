-- AI subscriptions and external adapters are priced by environment variables only:
-- API_CWAI_PRICE_(INPUT|OUTPUT)_<name> and API_CWAI_TOKENS_(INPUT|OUTPUT)_<name>.
-- The pricing columns V107 gave ai_subscription are therefore dropped. The legacy
-- ones of ai_adapter (V103) are kept, unused, so no existing data is destroyed.
ALTER TABLE ai_subscription
    DROP COLUMN IF EXISTS billing_enabled,
    DROP COLUMN IF EXISTS input_tokens_per_unit,
    DROP COLUMN IF EXISTS input_price_per_unit,
    DROP COLUMN IF EXISTS output_tokens_per_unit,
    DROP COLUMN IF EXISTS output_price_per_unit,
    DROP COLUMN IF EXISTS divide_blocks;
