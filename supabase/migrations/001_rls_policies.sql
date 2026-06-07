-- Row Level Security policies for Supabase
-- Service role (backend) bypasses RLS; anon/authenticated use policies below.

ALTER TABLE partners ENABLE ROW LEVEL SECURITY;
ALTER TABLE partner_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE partner_commissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE partner_payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE booking_reservations ENABLE ROW LEVEL SECURITY;
ALTER TABLE booking_passengers ENABLE ROW LEVEL SECURITY;
ALTER TABLE booking_payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE booking_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE partner_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE access_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Partners: public read only active partners (limited columns via view recommended in production)
CREATE POLICY partners_public_read ON partners
  FOR SELECT USING (active = true);

-- Partner users see own partner data
CREATE POLICY partner_commissions_own ON partner_commissions
  FOR SELECT USING (
    partner_id IN (
      SELECT partner_id FROM partner_users WHERE id = auth.uid()::uuid
    )
  );

-- Deny direct client writes on reservations (engine service role only)
CREATE POLICY reservations_service_only ON booking_reservations
  FOR ALL USING (false);

-- Admin tables: no public access
CREATE POLICY admin_users_deny ON admin_users FOR ALL USING (false);

COMMENT ON POLICY reservations_service_only ON booking_reservations IS
  'Reservations managed exclusively by Motor de Reservas API (service role).';
