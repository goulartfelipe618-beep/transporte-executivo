(function (global) {
  "use strict";

  const STRINGS = {
    pt: {
      lang_label: "Idioma",
      step_trip: "Viagem",
      step_vehicle: "Veículo",
      step_confirm: "Confirmar",
      how_title: "Como funciona",
      how_body: "1) Informe seu trajeto · 2) Escolha o veículo · 3) Confirme. Você recebe o número da solicitação na hora.",
      pay_title: "Pagamento",
      pay_body: "O valor é pago somente na hora de descer do veículo — dinheiro, cartão ou PIX, conforme disponível com o motorista.",
      title_step1: "Para onde você vai?",
      lead_step1: "Leva menos de 1 minuto. Sem cadastro.",
      trip_one_way: "Ida",
      trip_round: "Ida e Volta",
      trip_hourly: "Por Hora",
      section_outbound: "Ida",
      section_return: "Volta",
      origin: "Origem",
      destination: "Destino",
      date: "Data",
      time: "Hora",
      return_origin: "De onde você será buscado na volta?",
      return_origin_hint: "Normalmente o mesmo local para onde você foi na ida (ex.: aeroporto).",
      return_destination: "Destino da volta",
      return_destination_hint: "Sempre o mesmo ponto de partida da ida.",
      return_date: "Data da volta",
      return_time: "Hora da volta",
      hourly_hours: "Quantas horas?",
      hourly_hint: "Veículo à disposição com motorista.",
      your_data: "Seus dados",
      name: "Nome completo",
      whatsapp: "WhatsApp",
      btn_vehicles: "VER OPÇÕES DISPONÍVEIS",
      btn_loading: "Buscando opções…",
      placeholder_origin: "Endereço de partida",
      placeholder_dest: "Para onde você vai?",
      title_step2: "Escolha seu veículo",
      lead_step2: "Toque na opção desejada. Valor estimado.",
      title_step2_type: "Escolha o tipo de veículo",
      lead_step2_type: "Tipos disponíveis na sua região. Toque para ver os veículos.",
      lead_step2_detail: "Toque no veículo desejado. Valor estimado.",
      types_loading: "Carregando tipos…",
      btn_back_type: "← Voltar aos tipos",
      one_vehicle: "1 veículo disponível",
      vehicles_available: "veículos disponíveis",
      price_on_request: "Valor sob consulta",
      no_types: "Nenhum tipo de veículo disponível nesta região.",
      no_vehicles_type: "Nenhum veículo deste tipo na região.",
      pax: "passageiros",
      bags: "bagagens",
      title_step3: "Confirme sua solicitação",
      summary_total: "Total estimado",
      summary_route: "Trajeto ida",
      summary_return: "Trajeto volta",
      summary_when: "Quando (ida)",
      summary_return_when: "Quando (volta)",
      summary_vehicle: "Veículo",
      summary_contact: "Contato",
      pay_reminder: "Pagamento apenas ao descer do veículo.",
      lgpd: "Aceito o uso dos meus dados conforme a LGPD.",
      btn_confirm: "CONFIRMAR SOLICITAÇÃO",
      btn_confirming: "Confirmando…",
      title_done: "Solicitação enviada!",
      done_lead: "Guarde seu número:",
      done_whatsapp: "Falar no WhatsApp",
      done_new: "Nova solicitação",
      err_generic: "Não foi possível continuar. Tente novamente.",
      err_lgpd: "Aceite os termos para continuar.",
      err_return: "Preencha origem, data e hora da volta.",
    },
    es: {
      lang_label: "Idioma",
      step_trip: "Viaje",
      step_vehicle: "Vehículo",
      step_confirm: "Confirmar",
      how_title: "Cómo funciona",
      how_body: "1) Indique su trayecto · 2) Elija el vehículo · 3) Confirme. Recibirá el número de solicitud al instante.",
      pay_title: "Pago",
      pay_body: "El importe se paga solo al bajar del vehículo — efectivo, tarjeta o PIX, según disponibilidad del conductor.",
      title_step1: "¿A dónde va?",
      lead_step1: "Menos de 1 minuto. Sin registro.",
      trip_one_way: "Ida",
      trip_round: "Ida y Vuelta",
      trip_hourly: "Por Hora",
      section_outbound: "Ida",
      section_return: "Vuelta",
      origin: "Origen",
      destination: "Destino",
      date: "Fecha",
      time: "Hora",
      return_origin: "¿Desde dónde le recogen en la vuelta?",
      return_origin_hint: "Normalmente el mismo lugar al que fue en la ida (ej.: aeropuerto).",
      return_destination: "Destino de la vuelta",
      return_destination_hint: "Siempre el mismo punto de partida de la ida.",
      return_date: "Fecha de vuelta",
      return_time: "Hora de vuelta",
      hourly_hours: "¿Cuántas horas?",
      hourly_hint: "Vehículo a disposición con conductor.",
      your_data: "Sus datos",
      name: "Nombre completo",
      whatsapp: "WhatsApp",
      btn_vehicles: "VER OPCIONES DISPONIBLES",
      btn_loading: "Buscando opciones…",
      placeholder_origin: "Dirección de salida",
      placeholder_dest: "¿A dónde va?",
      title_step2: "Elija su vehículo",
      lead_step2: "Toque la opción deseada. Precio estimado.",
      title_step2_type: "Elija el tipo de vehículo",
      lead_step2_type: "Tipos disponibles en su región. Toque para ver los vehículos.",
      lead_step2_detail: "Toque el vehículo deseado. Precio estimado.",
      types_loading: "Cargando tipos…",
      btn_back_type: "← Volver a los tipos",
      one_vehicle: "1 vehículo disponible",
      vehicles_available: "vehículos disponibles",
      price_on_request: "Precio a consultar",
      no_types: "No hay tipos de vehículo disponibles en esta región.",
      no_vehicles_type: "No hay vehículos de este tipo en la región.",
      pax: "pasajeros",
      bags: "equipajes",
      title_step3: "Confirme su solicitud",
      summary_total: "Total estimado",
      summary_route: "Trayecto ida",
      summary_return: "Trayecto vuelta",
      summary_when: "Cuándo (ida)",
      summary_return_when: "Cuándo (vuelta)",
      summary_vehicle: "Vehículo",
      summary_contact: "Contacto",
      pay_reminder: "Pago solo al bajar del vehículo.",
      lgpd: "Acepto el uso de mis datos conforme a la LGPD.",
      btn_confirm: "CONFIRMAR SOLICITUD",
      btn_confirming: "Confirmando…",
      title_done: "¡Solicitud enviada!",
      done_lead: "Guarde su número:",
      done_whatsapp: "Hablar por WhatsApp",
      done_new: "Nueva solicitud",
      err_generic: "No fue posible continuar. Intente de nuevo.",
      err_lgpd: "Acepte los términos para continuar.",
      err_return: "Complete origen, fecha y hora de la vuelta.",
    },
    en: {
      lang_label: "Language",
      step_trip: "Trip",
      step_vehicle: "Vehicle",
      step_confirm: "Confirm",
      how_title: "How it works",
      how_body: "1) Enter your route · 2) Pick a vehicle · 3) Confirm. You get your request number instantly.",
      pay_title: "Payment",
      pay_body: "Pay only when you get out of the vehicle — cash, card or PIX, subject to driver availability.",
      title_step1: "Where are you going?",
      lead_step1: "Takes under 1 minute. No sign-up.",
      trip_one_way: "One way",
      trip_round: "Round trip",
      trip_hourly: "Hourly",
      section_outbound: "Outbound",
      section_return: "Return",
      origin: "Pickup",
      destination: "Destination",
      date: "Date",
      time: "Time",
      return_origin: "Where should we pick you up for the return?",
      return_origin_hint: "Usually the same place you went on the outbound trip (e.g. airport).",
      return_destination: "Return destination",
      return_destination_hint: "Always the same as your original pickup point.",
      return_date: "Return date",
      return_time: "Return time",
      hourly_hours: "How many hours?",
      hourly_hint: "Vehicle with driver at your disposal.",
      your_data: "Your details",
      name: "Full name",
      whatsapp: "WhatsApp",
      btn_vehicles: "SEE AVAILABLE OPTIONS",
      btn_loading: "Searching options…",
      placeholder_origin: "Pickup address",
      placeholder_dest: "Where to?",
      title_step2: "Choose your vehicle",
      lead_step2: "Tap your preferred option. Estimated price.",
      title_step2_type: "Choose vehicle type",
      lead_step2_type: "Types available in your region. Tap to see vehicles.",
      lead_step2_detail: "Tap the vehicle you want. Estimated price.",
      types_loading: "Loading types…",
      btn_back_type: "← Back to types",
      one_vehicle: "1 vehicle available",
      vehicles_available: "vehicles available",
      price_on_request: "Price on request",
      no_types: "No vehicle types available in this region.",
      no_vehicles_type: "No vehicles of this type in the region.",
      pax: "passengers",
      bags: "bags",
      title_step3: "Confirm your request",
      summary_total: "Estimated total",
      summary_route: "Outbound route",
      summary_return: "Return route",
      summary_when: "When (outbound)",
      summary_return_when: "When (return)",
      summary_vehicle: "Vehicle",
      summary_contact: "Contact",
      pay_reminder: "Payment only when you exit the vehicle.",
      lgpd: "I accept use of my data under LGPD.",
      btn_confirm: "CONFIRM REQUEST",
      btn_confirming: "Confirming…",
      title_done: "Request sent!",
      done_lead: "Save your number:",
      done_whatsapp: "Open WhatsApp",
      done_new: "New request",
      err_generic: "Could not continue. Please try again.",
      err_lgpd: "Please accept the terms to continue.",
      err_return: "Fill in return pickup, date and time.",
    },
  };

  const LANG_LABELS = { pt: "PT", es: "ES", en: "EN" };

  function detectLang() {
    const saved = localStorage.getItem("express_lang");
    if (saved && STRINGS[saved]) return saved;
    const nav = (navigator.language || "pt").slice(0, 2).toLowerCase();
    if (nav === "es") return "es";
    if (nav === "en") return "en";
    return "pt";
  }

  let currentLang = detectLang();

  function t(key) {
    return (STRINGS[currentLang] && STRINGS[currentLang][key]) || STRINGS.pt[key] || key;
  }

  function setLang(lang) {
    if (!STRINGS[lang]) return;
    currentLang = lang;
    localStorage.setItem("express_lang", lang);
    document.documentElement.lang = lang === "pt" ? "pt-BR" : lang;
    apply();
    document.dispatchEvent(new CustomEvent("express:lang", { detail: { lang } }));
  }

  function apply() {
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.dataset.i18n;
      const val = t(key);
      if (val) el.textContent = val;
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      const key = el.dataset.i18nPlaceholder;
      const val = t(key);
      if (val) el.placeholder = val;
    });
    document.querySelectorAll("[data-i18n-title]").forEach((el) => {
      const key = el.dataset.i18nTitle;
      const val = t(key);
      if (val) el.title = val;
    });
    document.querySelectorAll(".lang-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.lang === currentLang);
      btn.setAttribute("aria-pressed", btn.dataset.lang === currentLang ? "true" : "false");
    });
  }

  function initLangBar() {
    document.querySelectorAll(".lang-btn").forEach((btn) => {
      btn.addEventListener("click", () => setLang(btn.dataset.lang));
    });
    apply();
  }

  global.ExpressI18n = { t, setLang, getLang: () => currentLang, LANG_LABELS, initLangBar };
})(window);
