-- Portal motorista: mini painel, reservas proprias e identidade visual
ALTER TABLE public.drivers ADD COLUMN IF NOT EXISTS portal_panel jsonb DEFAULT '{}'::jsonb;

ALTER TABLE public.reservations ADD COLUMN IF NOT EXISTS owner_type text;
ALTER TABLE public.reservations ADD COLUMN IF NOT EXISTS created_by_driver_id text;
ALTER TABLE public.reservations ADD COLUMN IF NOT EXISTS created_by_driver_name text;
ALTER TABLE public.reservations ADD COLUMN IF NOT EXISTS client_kind text;

COMMENT ON COLUMN public.drivers.portal_panel IS 'Configuracoes do mini painel do motorista (logo, contrato, 2FA e identidade visual)';
COMMENT ON COLUMN public.reservations.owner_type IS 'Origem de propriedade da reserva: operacao, motorista, rede etc.';
COMMENT ON COLUMN public.reservations.created_by_driver_id IS 'ID legado do motorista que criou a reserva pelo portal motorista';
COMMENT ON COLUMN public.reservations.created_by_driver_name IS 'Nome do motorista que criou a reserva pelo portal motorista';
COMMENT ON COLUMN public.reservations.client_kind IS 'Tipo do cliente usado no cadastro centralizado da reserva';
