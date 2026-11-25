-- ai-instruct-11: AI subscriptions replace the hard-coded model adapters.
-- A subscription is global (not owned by a user): every user with the cwaiapi
-- flag can prompt through it, only admins can manage it.
CREATE TABLE IF NOT EXISTS ai_subscription (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    base_url TEXT NOT NULL,
    model VARCHAR(255) NOT NULL,
    max_tokens INT NOT NULL DEFAULT 4096,
    token TEXT NOT NULL,
    position INT NOT NULL DEFAULT 0,
    billing_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    input_tokens_per_unit INT,
    input_price_per_unit FLOAT,
    output_tokens_per_unit INT,
    output_price_per_unit FLOAT,
    divide_blocks BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_ai_subscription_name UNIQUE (name)
);

-- External adapters can be shared by their owner with other cwaiapi users
-- (the right to prompt through it, never to edit it).
CREATE TABLE IF NOT EXISTS ai_adapter_share (
    adapter_id uuid NOT NULL REFERENCES ai_adapter(id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (adapter_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_ai_adapter_share_user_id ON ai_adapter_share(user_id);
