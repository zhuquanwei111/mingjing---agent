ALTER TABLE public.audit ADD COLUMN details jsonb NOT NULL DEFAULT '{}'::jsonb;

REVOKE INSERT, UPDATE ON public.subjects FROM p2_app;
REVOKE SELECT, INSERT, UPDATE ON public.credentials FROM p2_app;

CREATE FUNCTION public.authenticate_identity(credential_id uuid, token_fingerprint text)
RETURNS TABLE (id uuid, tenant text, subject text, administrator boolean)
LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog
AS $$
    SELECT c.id, c.tenant, c.subject, s.administrator
    FROM public.credentials c JOIN public.subjects s USING (tenant, subject)
    WHERE CASE WHEN credential_id IS NOT NULL THEN c.id = credential_id
               ELSE c.fingerprint = token_fingerprint END
      AND NOT c.revoked AND c.expires_at > clock_timestamp() AND s.enabled
    FOR SHARE OF c, s
$$;

REVOKE ALL ON FUNCTION public.authenticate_identity(uuid, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.authenticate_identity(uuid, text) TO p2_app;
