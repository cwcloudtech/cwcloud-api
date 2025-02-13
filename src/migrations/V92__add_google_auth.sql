BEGIN;

ALTER TABLE public.user
ADD COLUMN google_id VARCHAR(255),
ADD COLUMN google_email VARCHAR(255),
ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'email';

CREATE INDEX idx_google_id ON public.user (google_id);

COMMIT;
