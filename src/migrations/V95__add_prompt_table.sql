CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE prompt_list (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255),
    user_id INT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE prompt (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_list_id uuid NOT NULL REFERENCES prompt_list(id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    sequence INT NOT NULL,
    prompt JSONB NOT NULL,
    answer JSONB NOT NULL,
    adapter VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    CONSTRAINT unique_prompt_sequence UNIQUE (prompt_list_id, sequence)
);

CREATE INDEX idx_prompt_prompt_list_id ON prompt(prompt_list_id);
CREATE INDEX idx_prompt_sequence ON prompt(prompt_list_id, sequence);
CREATE INDEX idx_prompt_list_user_id ON prompt_list(user_id);
CREATE INDEX idx_prompt_user_id ON prompt(user_id);
