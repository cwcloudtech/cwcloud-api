CREATE TABLE prompt_usage (
    cid uuid PRIMARY KEY,
    user_id INT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL,
    adapter VARCHAR(50) NOT NULL,
    prompt_tokens INT NOT NULL,
    completion_tokens INT NOT NULL,
    total_tokens INT NOT NULL
);

CREATE INDEX idx_prompt_usage_user_id ON prompt_usage(user_id);
CREATE INDEX idx_prompt_usage_created_at ON prompt_usage(created_at);
