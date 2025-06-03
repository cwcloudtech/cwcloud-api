CREATE TABLE storage_kv (
    id uuid PRIMARY KEY,
    storage_key VARCHAR(255) NOT NULL,
    user_id INT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    payload JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE UNIQUE INDEX idx_storage_kv_user_key ON storage_kv(user_id, storage_key);

CREATE INDEX idx_storage_kv_user_id ON storage_kv(user_id);
CREATE INDEX idx_storage_kv_key ON storage_kv(storage_key);
CREATE INDEX idx_storage_kv_created_at ON storage_kv(created_at);
