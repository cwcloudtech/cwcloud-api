ALTER TABLE faas_function ADD COLUMN is_protected BOOLEAN NOT NULL DEFAULT false;
CREATE INDEX idx_faas_function_is_protected ON faas_function (is_protected);
