-- Portal motorista: campos de ativacao (token uso unico + senha)
ALTER TABLE drivers ADD COLUMN IF NOT EXISTS activation_expires_at timestamptz;
ALTER TABLE drivers ADD COLUMN IF NOT EXISTS activation_token_consumed_at text;
ALTER TABLE drivers ADD COLUMN IF NOT EXISTS portal_activated_at text;

COMMENT ON COLUMN drivers.activation_token IS 'Token de primeiro acesso (uso unico, 72h)';
COMMENT ON COLUMN drivers.activation_token_consumed_at IS 'Data/hora em que o motorista consumiu o token no portal';
COMMENT ON COLUMN drivers.portal_activated_at IS 'Data/hora em que a senha permanente foi definida';
