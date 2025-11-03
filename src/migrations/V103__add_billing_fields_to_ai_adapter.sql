ALTER TABLE ai_adapter 
ADD COLUMN billing_enabled BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN input_tokens_per_unit INTEGER,
ADD COLUMN input_price_per_unit FLOAT,
ADD COLUMN output_tokens_per_unit INTEGER,
ADD COLUMN output_price_per_unit FLOAT,
ADD COLUMN divide_blocks BOOLEAN NOT NULL DEFAULT TRUE;
