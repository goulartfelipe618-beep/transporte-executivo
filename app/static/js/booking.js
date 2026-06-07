/**
 * Nexus Transfer — Motor de Reservas UX
 */
const NexusBooking = (function () {
  const LOCATIONS_FALLBACK = [
    { name: 'Aeroporto Internacional de Guarulhos (GRU)', type: 'Aeroporto' },
    { name: 'Aeroporto Santos Dumont (SDU)', type: 'Aeroporto' },
    { name: 'Aeroporto de Congonhas (CGH)', type: 'Aeroporto' },
    { name: 'Hotel Copacabana Palace', type: 'Hotel' },
    { name: 'Hotel Unique São Paulo', type: 'Hotel' },
    { name: 'Centro de Convenções Expo Center Norte', type: 'Evento' },
    { name: 'Av. Paulista, 1000 — São Paulo', type: 'Endereço' },
    { name: 'Barra da Tijuca — Rio de Janeiro', type: 'Endereço' },
  ];

  let currentTripType = 'one_way';
  let selectedHours = 4;

  function toast(msg, isError) {
    const el = document.createElement('div');
    el.className = 'feedback-toast' + (isError ? ' error' : '');
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 4000);
  }

  function setLoading(btn, loading) {
    if (!btn) return;
    btn.disabled = loading;
    btn.classList.toggle('btn-loading', loading);
  }

  async function fetchLocations(q) {
    try {
      const res = await fetch('/api/v1/public/locations?q=' + encodeURIComponent(q), { credentials: 'include' });
      const data = await res.json();
      const items = data.items || [];
      if (items.length) return items.map((i) => (typeof i === 'string' ? { name: i, type: '' } : i));
    } catch (_) {}
    return LOCATIONS_FALLBACK.filter((l) => l.name.toLowerCase().includes(q.toLowerCase()));
  }

  function setupAutocomplete(input) {
    const wrap = input.closest('.autocomplete-wrap') || input.parentElement;
    let list = wrap.querySelector('.autocomplete-list');
    if (!list) {
      list = document.createElement('div');
      list.className = 'autocomplete-list';
      wrap.appendChild(list);
    }
    let debounce;
    input.addEventListener('input', () => {
      clearTimeout(debounce);
      const q = input.value.trim();
      if (q.length < 2) {
        list.classList.remove('show');
        return;
      }
      debounce = setTimeout(async () => {
        const items = await fetchLocations(q);
        list.innerHTML = items
          .slice(0, 8)
          .map(
            (i) =>
              `<div class="autocomplete-item" data-value="${escapeAttr(i.name || i)}">${i.name || i}<small>${i.type || ''}</small></div>`
          )
          .join('');
        list.classList.add('show');
        list.querySelectorAll('.autocomplete-item').forEach((el) => {
          el.addEventListener('click', () => {
            input.value = el.dataset.value;
            list.classList.remove('show');
            updateRouteEstimate();
          });
        });
      }, 280);
    });
    document.addEventListener('click', (e) => {
      if (!wrap.contains(e.target)) list.classList.remove('show');
    });
  }

  function escapeAttr(s) {
    return String(s).replace(/"/g, '&quot;');
  }

  function initTripTypeSwitcher() {
    document.querySelectorAll('.trip-type-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        currentTripType = btn.dataset.trip;
        document.querySelectorAll('.trip-type-btn').forEach((b) => {
          b.classList.toggle('active', b === btn);
          b.setAttribute('aria-selected', b === btn ? 'true' : 'false');
        });
        document.querySelectorAll('.trip-form-panel').forEach((p) => p.classList.remove('active'));
        const panel = document.getElementById('panel-' + currentTripType);
        if (panel) panel.classList.add('active');
        updateRouteEstimate();
      });
    });

    document.querySelectorAll('.hour-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        document.querySelectorAll('.hour-chip').forEach((c) => c.classList.remove('active'));
        chip.classList.add('active');
        selectedHours = parseInt(chip.dataset.hours, 10);
        const hidden = document.getElementById('hourly_hours');
        if (hidden) hidden.value = selectedHours;
      });
    });
  }

  function getOriginDestination() {
    if (currentTripType === 'hourly') {
      const city = document.getElementById('city')?.value || '';
      return { origin: city, destination: `À disposição (${selectedHours}h)` };
    }
    if (currentTripType === 'round_trip') {
      return {
        origin: document.getElementById('origin_rt')?.value || '',
        destination: document.getElementById('destination_rt')?.value || '',
      };
    }
    return {
      origin: document.getElementById('origin')?.value || '',
      destination: document.getElementById('destination')?.value || '',
    };
  }

  function updateRouteEstimate() {
    const { origin, destination } = getOriginDestination();
    const bar = document.getElementById('route-estimate');
    if (!bar || !origin || origin.length < 3) return;
    const seed = (origin + destination).split('').reduce((a, c) => a + c.charCodeAt(0), 0);
    const km = 15 + (seed % 85);
    const min = 30 + (seed % 90);
    document.getElementById('est-distance').textContent = km + ' km';
    document.getElementById('est-duration').textContent = min + ' min';
    bar.classList.remove('hidden');
    initRouteMap(origin, destination);
  }

  let mapInstance;
  function initRouteMap(origin, destination) {
    const el = document.getElementById('route-map');
    if (!el || typeof L === 'undefined') return;
    if (!origin) {
      origin = el.dataset.origin;
      destination = el.dataset.destination;
    }
    if (!origin) return;
    el.classList.remove('hidden');
    if (mapInstance) {
      mapInstance.remove();
      mapInstance = null;
    }
    const seed = (origin + (destination || '')).split('').reduce((a, c) => a + c.charCodeAt(0), 0);
    const lat = -23.55 + (seed % 100) / 500;
    const lng = -46.63 + (seed % 80) / 400;
    mapInstance = L.map(el).setView([lat, lng], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap',
    }).addTo(mapInstance);
    L.marker([lat, lng]).addTo(mapInstance).bindPopup(origin).openPopup();
    if (destination) {
      L.marker([lat + 0.05, lng + 0.04]).addTo(mapInstance).bindPopup(destination);
      L.polyline([[lat, lng], [lat + 0.05, lng + 0.04]], { color: '#D4AF37', weight: 4 }).addTo(mapInstance);
    }
  }

  function buildSearchPayload() {
    const passengers = parseInt(document.getElementById('passengers')?.value || 1, 10);
    const luggage = parseInt(document.getElementById('luggage')?.value || 0, 10);
    const notes = document.getElementById('notes')?.value || null;

    if (currentTripType === 'hourly') {
      return {
        trip_type: 'hourly',
        city: document.getElementById('city')?.value,
        trip_date: document.getElementById('trip_date_h')?.value,
        trip_time: document.getElementById('trip_time_h')?.value,
        hourly_hours: selectedHours,
        passengers,
        luggage,
        notes,
      };
    }

    if (currentTripType === 'round_trip') {
      return {
        trip_type: 'round_trip',
        origin: document.getElementById('origin_rt')?.value,
        destination: document.getElementById('destination_rt')?.value,
        trip_date: document.getElementById('trip_date_rt')?.value,
        trip_time: document.getElementById('trip_time_rt')?.value,
        return_date: document.getElementById('return_date')?.value,
        return_time: document.getElementById('return_time')?.value,
        passengers,
        luggage,
        notes,
      };
    }

    return {
      trip_type: 'one_way',
      origin: document.getElementById('origin')?.value,
      destination: document.getElementById('destination')?.value,
      trip_date: document.getElementById('trip_date_ow')?.value,
      trip_time: document.getElementById('trip_time_ow')?.value,
      passengers,
      luggage,
      notes,
    };
  }

  function initSearch() {
    initTripTypeSwitcher();
    document.querySelectorAll('[data-autocomplete], #city').forEach(setupAutocomplete);
    ['origin', 'destination', 'origin_rt', 'destination_rt', 'city'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('blur', updateRouteEstimate);
    });

    const form = document.getElementById('search-form');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = document.getElementById('btn-search');
      setLoading(btn, true);
      try {
        const body = buildSearchPayload();
        const res = await fetch('/api/v1/booking/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(body),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          toast(data.detail?.[0]?.msg || data.detail || 'Verifique os campos da busca', true);
          return;
        }
        toast('Veículos encontrados! Redirecionando...');
        setTimeout(() => {
          window.location.href = '/booking/' + data.id + '/vehicles';
        }, 400);
      } catch (_) {
        toast('Erro de conexão. Tente novamente.', true);
      } finally {
        setLoading(btn, false);
      }
    });

    syncDateInputs();
  }

  function syncDateInputs() {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const min = tomorrow.toISOString().split('T')[0];
    document.querySelectorAll('input[type="date"]').forEach((inp) => {
      inp.min = min;
      if (!inp.value) inp.value = min;
    });
    document.querySelectorAll('input[type="time"]').forEach((inp) => {
      if (!inp.value) inp.value = '10:00';
    });
  }

  function initVehicleSelect() {
    document.querySelectorAll('.select-vehicle').forEach((btn) => {
      btn.addEventListener('click', async () => {
        setLoading(btn, true);
        const rid = btn.dataset.reservation;
        const vehicle = {
          category: btn.dataset.category,
          name: btn.dataset.name,
          brand: btn.dataset.brand || null,
          model: btn.dataset.model || null,
          price: parseFloat(btn.dataset.price),
          image_url: btn.dataset.image || null,
          benefits: (btn.dataset.benefits || '').split('|').filter(Boolean),
        };
        try {
          const res = await fetch('/api/v1/booking/' + rid + '/vehicle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(vehicle),
          });
          if (res.ok) {
            toast('Veículo selecionado!');
            window.location.href = '/booking/' + rid + '/passenger';
          } else toast('Não foi possível selecionar o veículo', true);
        } finally {
          setLoading(btn, false);
        }
      });
    });
  }

  function initPassenger(reservationId) {
    const form = document.getElementById('passenger-form');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = form.querySelector('[type="submit"]');
      setLoading(btn, true);
      const fd = new FormData(form);
      const body = {
        full_name: fd.get('full_name'),
        phone: fd.get('phone'),
        whatsapp: fd.get('whatsapp') || null,
        email: fd.get('email'),
        cpf: fd.get('cpf'),
        company: fd.get('company') || null,
        flight_number: fd.get('flight_number') || null,
        notes: fd.get('notes') || null,
        lgpd_accepted: fd.get('lgpd_accepted') === '1',
      };
      try {
        const res = await fetch('/api/v1/booking/' + reservationId + '/passenger', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(body),
        });
        if (res.ok) window.location.href = '/booking/' + reservationId + '/summary';
        else {
          const err = await res.json().catch(() => ({}));
          toast(err.detail?.[0]?.msg || err.detail || 'Verifique os dados', true);
        }
      } finally {
        setLoading(btn, false);
      }
    });
  }

  function initPayment(reservationId) {
    document.querySelectorAll('.payment-option').forEach((opt) => {
      opt.addEventListener('click', () => {
        document.querySelectorAll('.payment-option').forEach((o) => o.classList.remove('selected'));
        opt.classList.add('selected');
        opt.querySelector('input').checked = true;
      });
    });

    document.getElementById('btn-pay')?.addEventListener('click', async () => {
      const btn = document.getElementById('btn-pay');
      setLoading(btn, true);
      const method = document.querySelector('input[name="pay_method"]:checked')?.value || 'pix';
      let provider = 'pix';
      let payMethod = 'pix';
      if (method === 'card_mp') {
        provider = 'mercadopago';
        payMethod = 'card';
      } else if (method === 'card_stripe') {
        provider = 'stripe';
        payMethod = 'card';
      } else if (method === 'corporate') {
        provider = 'corporate';
        payMethod = 'invoice';
      }
      try {
        await fetch('/api/v1/booking/' + reservationId + '/payment', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ provider, method: payMethod }),
        });
        const confirm = await fetch('/api/v1/booking/' + reservationId + '/confirm', {
          method: 'POST',
          credentials: 'include',
        });
        if (confirm.ok) window.location.href = '/booking/' + reservationId + '/confirmation';
        else toast('Erro na confirmação do pagamento', true);
      } catch (_) {
        toast('Erro de conexão', true);
      } finally {
        setLoading(btn, false);
      }
    });
  }

  function initConfirmation(code) {
    document.getElementById('btn-email')?.addEventListener('click', () => {
      toast('E-mail de confirmação será enviado em produção (SMTP configurado).');
    });
    document.getElementById('btn-whatsapp')?.addEventListener('click', () => {
      const text = encodeURIComponent('Minha reserva Nexus Transfer: ' + code);
      window.open('https://wa.me/?text=' + text, '_blank');
    });
  }

  return {
    initSearch,
    initVehicleSelect,
    initPassenger,
    initPayment,
    initConfirmation,
    initRouteMap,
  };
})();
