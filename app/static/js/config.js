const MOTOR_API_BASE = "http://127.0.0.1:8770";
const MOTOR_LOCAL_API = window.location.origin;

const GatewayAPI = {
  network: (slug, codigo) => `${MOTOR_API_BASE}/api/v1/network/${encodeURIComponent(slug)}/${encodeURIComponent(codigo)}`,
  vehicles: () => `${MOTOR_API_BASE}/vehicles`,
  quote: () => `${MOTOR_API_BASE}/quote`,
  reserve: () => `${MOTOR_API_BASE}/reserve`,
};

const ExpressAPI = {
  network: (slug, codigo) => `${MOTOR_LOCAL_API}/api/v1/express/network/${encodeURIComponent(slug)}/${encodeURIComponent(codigo)}`,
  start: () => `${MOTOR_LOCAL_API}/api/v1/express/start`,
  vehicleTypes: (id) => `${MOTOR_LOCAL_API}/api/v1/express/${id}/vehicle-types`,
  vehicles: (id, type) => `${MOTOR_LOCAL_API}/api/v1/express/${id}/vehicles?type=${encodeURIComponent(type)}`,
  vehicle: (id) => `${MOTOR_LOCAL_API}/api/v1/express/${id}/vehicle`,
  summary: (id) => `${MOTOR_LOCAL_API}/api/v1/express/${id}/summary`,
  confirm: (id) => `${MOTOR_LOCAL_API}/api/v1/express/${id}/confirm`,
};

window.MOTOR_API_BASE = MOTOR_API_BASE;
window.GatewayAPI = GatewayAPI;
window.ExpressAPI = ExpressAPI;
