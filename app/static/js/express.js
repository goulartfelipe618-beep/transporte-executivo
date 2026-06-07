(function () {
  "use strict";

  function qs(s, r) { return (r || document).querySelector(s); }
  function qsa(s, r) { return Array.from((r || document).querySelectorAll(s)); }
  function t(key) { return window.ExpressI18n ? ExpressI18n.t(key) : key; }
  function showError(el, msg) {
    if (!el) return;
    el.textContent = msg || "";
    el.classList.toggle("hidden", !msg);
  }
  function getRef() {
    return new URLSearchParams(window.location.search).get("ref") || "";
  }

  function defaultDateTime(form) {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    const dateEl = qs("#trip_date", form);
    const timeEl = qs("#trip_time", form);
    const today = now.toISOString().slice(0, 10);
    if (dateEl && !dateEl.value) {
      dateEl.min = today;
      dateEl.value = today;
    }
    if (timeEl && !timeEl.value) {
      const mins = now.getMinutes();
      const add = mins < 30 ? 30 - mins : 60 - mins;
      now.setMinutes(mins + add, 0, 0);
      timeEl.value = `${pad(now.getHours())}:${pad(now.getMinutes())}`;
    }
    const retDate = qs("#return_date", form);
    if (retDate && !retDate.min && dateEl) retDate.min = dateEl.value || today;
  }

  function syncReturnDestination(form) {
    const origin = qs("#origin", form);
    const retDest = qs("#return_destination", form);
    if (origin && retDest) retDest.value = origin.value;
  }

  function syncReturnOriginFromDestination(form, force) {
    const dest = qs("#destination", form);
    const retOrigin = qs("#return_origin", form);
    if (!dest || !retOrigin) return;
    if (force || !retOrigin.dataset.userEdited) {
      retOrigin.value = dest.value;
    }
  }

  function initTripPills() {
    const form = qs("#express-form-step1");
    if (!form) return;
    const tripInput = qs("#trip_type", form);
    const returnFields = qs("#return-fields", form);
    const hourlyFields = qs("#hourly-fields", form);
    const destField = qs("#field-destination", form);
    const destInput = qs("#destination", form);
    const retOrigin = qs("#return_origin", form);
    const retDate = qs("#return_date", form);
    const retTime = qs("#return_time", form);

    function setTripMode(trip) {
      returnFields.classList.toggle("hidden", trip !== "round_trip");
      hourlyFields.classList.toggle("hidden", trip !== "hourly");
      destField.classList.toggle("hidden", trip === "hourly");
      if (trip === "hourly") {
        destInput.removeAttribute("required");
      } else {
        destInput.setAttribute("required", "");
      }
      if (trip === "round_trip") {
        retOrigin.setAttribute("required", "");
        retDate.setAttribute("required", "");
        retTime.setAttribute("required", "");
        syncReturnDestination(form);
        syncReturnOriginFromDestination(form, false);
      } else {
        retOrigin.removeAttribute("required");
        retDate.removeAttribute("required");
        retTime.removeAttribute("required");
      }
    }

    qsa(".trip-pills .pill", form).forEach((btn) => {
      btn.addEventListener("click", () => {
        qsa(".trip-pills .pill", form).forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        tripInput.value = btn.dataset.trip;
        setTripMode(btn.dataset.trip);
      });
    });

    qs("#origin", form)?.addEventListener("input", () => syncReturnDestination(form));
    qs("#destination", form)?.addEventListener("input", () => {
      if (tripInput.value === "round_trip") syncReturnOriginFromDestination(form, false);
    });
    retOrigin?.addEventListener("input", () => { retOrigin.dataset.userEdited = "1"; });
    qs("#trip_date", form)?.addEventListener("change", (e) => {
      if (retDate) retDate.min = e.target.value;
    });

    defaultDateTime(form);
    syncReturnDestination(form);
  }

  function initStep1() {
    const form = qs("#express-form-step1");
    if (!form) return;
    initTripPills();

    const slug = form.dataset.slug;
    const codigo = form.dataset.codigo;
    const err = qs("#form-error", form);
    const btn = qs("#btn-step1", form);
    const ref = form.dataset.contributorRef || getRef();

    if (form.dataset.isHotel === "1") {
      const dest = qs("#destination", form);
      if (dest) dest.focus();
    }

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      showError(err, "");
      const tripType = qs("#trip_type", form).value;

      if (tripType === "round_trip") {
        const ro = qs("#return_origin", form).value.trim();
        const rd = qs("#return_date", form).value;
        const rt = qs("#return_time", form).value;
        if (!ro || !rd || !rt) {
          showError(err, t("err_return"));
          return;
        }
      }

      btn.disabled = true;
      const prevLabel = btn.textContent;
      btn.textContent = t("btn_loading");

      let destination = qs("#destination", form).value.trim();
      if (tripType === "hourly") {
        const hours = parseInt(qs("#hourly_hours", form)?.value || "4", 10);
        destination = destination || `À disposição (${hours}h)`;
      }

      const payload = {
        trip_type: tripType,
        origin: qs("#origin", form).value.trim(),
        destination,
        trip_date: qs("#trip_date", form).value,
        trip_time: qs("#trip_time", form).value,
        passenger_name: qs("#passenger_name", form).value.trim(),
        passenger_whatsapp: qs("#passenger_whatsapp", form).value.trim(),
        slug: slug || undefined,
        codigo: codigo || undefined,
        contributor_ref: ref || undefined,
      };

      if (tripType === "round_trip") {
        payload.return_origin = qs("#return_origin", form).value.trim();
        payload.return_date = qs("#return_date", form).value;
        payload.return_time = qs("#return_time", form).value;
      }
      if (tripType === "hourly") {
        payload.hourly_hours = parseInt(qs("#hourly_hours", form)?.value || "4", 10);
      }

      try {
        const res = await fetch(ExpressAPI.start(), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(payload),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          const detail = data.detail;
          throw new Error(typeof detail === "string" ? detail : t("err_generic"));
        }
        window.location.href = data.redirect_url || `/express/${data.reservation_id}/veiculos`;
      } catch (ex) {
        showError(err, ex.message || t("err_generic"));
        btn.disabled = false;
        btn.textContent = t("btn_vehicles");
      }
    });

    document.addEventListener("express:lang", () => {
      if (!btn.disabled) btn.textContent = t("btn_vehicles");
    });
  }

  async function selectVehicle(card, rid, err) {
    card.classList.add("is-loading");
    try {
      const res = await fetch(ExpressAPI.vehicle(rid), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          vehicle_id: card.dataset.vehicleId,
          category: card.dataset.category,
          name: card.dataset.name,
          image_url: card.dataset.image || null,
          passengers: parseInt(card.dataset.passengers, 10) || 1,
          luggage: parseInt(card.dataset.luggage, 10) || 0,
          price: parseFloat(card.dataset.price) || 0,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || t("err_generic"));
      window.location.href = data.redirect_url || `/express/${rid}/resumo`;
    } catch (ex) {
      showError(err, ex.message);
      card.classList.remove("is-loading");
    }
  }

  function formatPrice(value) {
    const n = Number(value) || 0;
    return "R$ " + n.toFixed(2);
  }

  function renderTypeCard(item) {
    const minPrice = item.min_price != null ? formatPrice(item.min_price) : t("price_on_request");
    const countLabel = item.count === 1 ? t("one_vehicle") : `${item.count} ${t("vehicles_available")}`;
    return `
      <article class="vehicle-card type-card" tabindex="0" role="button"
        data-vehicle-type="${item.type}"
        data-type-label="${item.label}">
        <div class="vehicle-card-inner">
          <img src="${item.image_url || "/static/images/vehicles/sedan.svg"}" alt="" class="vehicle-img" loading="lazy">
          <div class="vehicle-info">
            <h2>${item.label}</h2>
            <p class="vehicle-meta">${countLabel}</p>
            <p class="vehicle-price">${minPrice}</p>
          </div>
          <span class="vehicle-chevron" aria-hidden="true">›</span>
        </div>
      </article>`;
  }

  function renderVehicleCard(v) {
    const name = v.name || v.category || "";
    const img = v.image_url || "/static/images/vehicles/sedan.svg";
    const brand = v.brand ? `<p class="vehicle-type">${v.brand}${v.model ? " " + v.model : ""}${v.year ? " · " + v.year : ""}</p>` : "";
    return `
      <article class="vehicle-card" tabindex="0" role="button"
        data-vehicle-id="${v.id || v.category}"
        data-category="${v.category || v.vehicle_type || ""}"
        data-name="${name}"
        data-image="${img}"
        data-passengers="${v.passengers || 1}"
        data-luggage="${v.luggage || 0}"
        data-price="${v.price || 0}">
        <div class="vehicle-card-inner">
          <img src="${img}" alt="" class="vehicle-img" loading="lazy">
          <div class="vehicle-info">
            <h2>${name}</h2>
            ${brand}
            <p class="vehicle-meta">${v.passengers || 1} <span data-i18n="pax">passageiros</span> · ${v.luggage || 0} <span data-i18n="bags">bagagens</span></p>
            <p class="vehicle-price">${formatPrice(v.price)}</p>
          </div>
          <span class="vehicle-chevron" aria-hidden="true">›</span>
        </div>
      </article>`;
  }

  async function loadVehicleTypes(rid, err) {
    const typesList = qs("#types-list");
    const loading = qs("#types-loading");
    if (!typesList) return;
    try {
      const res = await fetch(ExpressAPI.vehicleTypes(rid), { credentials: "include" });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || t("err_generic"));
      const items = data.items || [];
      if (loading) loading.remove();
      if (!items.length) {
        typesList.innerHTML = `<p class="express-empty">${t("no_types")}</p>`;
        return;
      }
      typesList.innerHTML = items.map(renderTypeCard).join("");
    } catch (ex) {
      if (loading) loading.remove();
      typesList.innerHTML = `<p class="express-empty">${t("no_types")}</p>`;
      showError(err, ex.message || t("err_generic"));
    }
  }

  async function loadVehiclesByType(rid, vehicleType, label, err) {
    const list = qs("#vehicles-list");
    const typePanel = qs("#type-panel");
    const detailPanel = qs("#detail-panel");
    const detailTitle = qs("#detail-title");
    if (!list || !detailPanel || !typePanel) return;

    typePanel.classList.add("hidden");
    detailPanel.classList.remove("hidden");
    if (detailTitle) detailTitle.textContent = label || vehicleType;
    list.innerHTML = `<p class="express-empty">${t("btn_loading")}</p>`;

    try {
      const res = await fetch(ExpressAPI.vehicles(rid, vehicleType), { credentials: "include" });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || t("err_generic"));
      const items = data.items || [];
      if (!items.length) {
        list.innerHTML = `<p class="express-empty">${t("no_vehicles_type")}</p>`;
        return;
      }
      list.innerHTML = items.map(renderVehicleCard).join("");
    } catch (ex) {
      list.innerHTML = `<p class="express-empty">${t("no_vehicles_type")}</p>`;
      showError(err, ex.message || t("err_generic"));
    }
  }

  function initStep2() {
    const step = qs("#vehicle-step");
    if (!step) return;
    const rid = step.dataset.reservationId;
    const err = qs("#form-error");
    const typesList = qs("#types-list");
    const vehiclesList = qs("#vehicles-list");
    const typePanel = qs("#type-panel");
    const detailPanel = qs("#detail-panel");

    loadVehicleTypes(rid, err);

    typesList?.addEventListener("click", (e) => {
      const card = e.target.closest(".type-card");
      if (!card || card.classList.contains("is-loading")) return;
      loadVehiclesByType(rid, card.dataset.vehicleType, card.dataset.typeLabel, err);
    });
    typesList?.addEventListener("keydown", (e) => {
      if (e.key !== "Enter" && e.key !== " ") return;
      const card = e.target.closest(".type-card");
      if (!card) return;
      e.preventDefault();
      loadVehiclesByType(rid, card.dataset.vehicleType, card.dataset.typeLabel, err);
    });

    qs("#btn-back-type")?.addEventListener("click", () => {
      detailPanel?.classList.add("hidden");
      typePanel?.classList.remove("hidden");
      showError(err, "");
      if (vehiclesList) vehiclesList.innerHTML = "";
    });

    vehiclesList?.addEventListener("click", (e) => {
      const card = e.target.closest(".vehicle-card:not(.type-card)");
      if (!card || card.classList.contains("is-loading")) return;
      selectVehicle(card, rid, err);
    });
    vehiclesList?.addEventListener("keydown", (e) => {
      if (e.key !== "Enter" && e.key !== " ") return;
      const card = e.target.closest(".vehicle-card:not(.type-card)");
      if (!card) return;
      e.preventDefault();
      selectVehicle(card, rid, err);
    });
  }

  function initStep3() {
    const form = qs("#express-form-step3");
    if (!form) return;
    const rid = form.dataset.reservationId;
    const err = qs("#form-error", form);
    const btn = form.querySelector('button[type="submit"]');

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!qs("#lgpd_accepted", form).checked) {
        showError(err, t("err_lgpd"));
        return;
      }
      showError(err, "");
      btn.disabled = true;
      btn.textContent = t("btn_confirming");

      try {
        const res = await fetch(ExpressAPI.confirm(rid), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ lgpd_accepted: true }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || t("err_generic"));
        window.location.href = data.redirect_url || `/express/${rid}/confirmado`;
      } catch (ex) {
        showError(err, ex.message);
        btn.disabled = false;
        btn.textContent = t("btn_confirm");
      }
    });

    document.addEventListener("express:lang", () => {
      if (!btn.disabled) btn.textContent = t("btn_confirm");
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (window.ExpressI18n) ExpressI18n.initLangBar();
    initStep1();
    initStep2();
    initStep3();
  });
})();
