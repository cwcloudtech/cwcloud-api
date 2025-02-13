BEGIN;

ALTER TABLE public.user
ADD COLUMN oidc_configs JSONB DEFAULT '[]'::jsonb;

-- Migrate existing Google OAuth data to the new array structure
UPDATE public.user
SET oidc_configs = jsonb_build_array(
    jsonb_build_object(
        'provider', 'google',
        'id', google_id,
        'email', google_email
    )
)
WHERE google_id IS NOT NULL;

ALTER TABLE public.user
DROP COLUMN google_id,
DROP COLUMN google_email,
DROP COLUMN auth_provider;

DROP INDEX IF EXISTS idx_google_id;

CREATE INDEX idx_oidc_configs ON public.user USING GIN (oidc_configs);

COMMIT;
