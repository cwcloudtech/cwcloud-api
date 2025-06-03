CREATE TABLE ai_adapter (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    user_id INT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    username VARCHAR,
    password VARCHAR,
    headers JSONB DEFAULT '{}'::jsonb,
    timeout INT DEFAULT 30,
    check_tls BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_ai_adapter_name UNIQUE (name, user_id)
);
