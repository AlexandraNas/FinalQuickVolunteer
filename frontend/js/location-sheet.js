/* QuickVolunteer · "Choose a location" panel, like a marketplace location picker.
   A pin button opens it: a colour map with a dot and the radius circle, the place
   name, "Locate me" and "Edit" (postcode or area, and the distance), and suggestions.
   Only the area is ever shown, never an exact address.

   window.QVLocation.open({
     title, place, centre: [lat, lng] or null, miles,
     dots: [{ at: [lat, lng], html }],          // tasks on Find a task
     editValue, editPlaceholder, editLabel,
     radiusOptions: [1, 3, 5] or null, radiusValue,
     suggestions: ["Hackney", ...],
     onApply({ value, miles }), onLocate({ postcode, area })
   }) */
(function () {
  "use strict";
  const MILE = 1609.34;
  let sheet = null;
  let map = null;
  let layer = null;
  let opts = {};
  let lastFocus = null;

  const esc = (v) => String(v == null ? "" : v)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

  function build() {
    sheet = document.createElement("div");
    sheet.className = "loc-sheet";
    sheet.hidden = true;
    sheet.innerHTML = `
      <div class="loc-sheet__backdrop" data-loc-close></div>
      <div class="loc-sheet__panel" role="dialog" aria-modal="true" aria-labelledby="loc-title">
        <span class="loc-sheet__grab" aria-hidden="true"></span>
        <div class="loc-sheet__head">
          <h2 id="loc-title">Choose a location</h2>
          <button class="loc-sheet__close" type="button" data-loc-close aria-label="Close">
            <img src="assets/icons/menu-close.svg" alt="" width="40" height="40">
          </button>
        </div>
        <div class="loc-sheet__card">
          <div class="loc-sheet__map" role="img" aria-label="Map of the area"></div>
          <div class="loc-sheet__info">
            <p class="loc-sheet__place" data-loc-place></p>
            <p class="loc-sheet__radius" data-loc-radius></p>
          </div>
          <div class="loc-sheet__actions">
            <button class="btn btn--primary" type="button" data-loc-locate>
              <img src="assets/icons/pin-white.svg" alt="" width="18" height="18">Locate me</button>
            <button class="btn loc-sheet__edit-btn" type="button" data-loc-edit>Edit</button>
          </div>
          <p class="form-error loc-sheet__error" role="alert" data-loc-error hidden></p>
          <form class="loc-sheet__form" data-loc-form hidden novalidate>
            <label class="loc-sheet__field"><span data-loc-edit-label>Postcode or area</span>
              <input type="search" data-loc-input autocomplete="postal-code"></label>
            <label class="loc-sheet__field" data-loc-radius-field><span>Distance</span>
              <select data-loc-radius-select></select></label>
            <button class="btn btn--primary" type="submit">Apply</button>
          </form>
        </div>
        <div class="loc-sheet__suggest" data-loc-suggest-box>
          <h3>Suggested for you</h3>
          <ul data-loc-suggest></ul>
        </div>
      </div>`;
    document.body.appendChild(sheet);

    sheet.addEventListener("click", (e) => {
      if (e.target.closest("[data-loc-close]")) close();
      else if (e.target.closest("[data-loc-locate]")) locate();
      else if (e.target.closest("[data-loc-edit]")) toggleEdit();
      else if (e.target.closest("[data-loc-pick]")) {
        apply(e.target.closest("[data-loc-pick]").dataset.locPick, opts.radiusValue);
      }
    });
    sheet.querySelector("[data-loc-form]").addEventListener("submit", (e) => {
      e.preventDefault();
      const select = sheet.querySelector("[data-loc-radius-select]");
      apply(sheet.querySelector("[data-loc-input]").value.trim(), opts.radiusOptions ? Number(select.value) || null : opts.radiusValue);
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && sheet && !sheet.hidden) close();
    });
  }

  function apply(value, miles) {
    if (typeof opts.onApply === "function") opts.onApply({ value, miles });
    close();
  }

  function toggleEdit(force) {
    const form = sheet.querySelector("[data-loc-form]");
    form.hidden = force === undefined ? !form.hidden : !force;
    if (!form.hidden) sheet.querySelector("[data-loc-input]").focus();
  }

  function showError(text) {
    const box = sheet.querySelector("[data-loc-error]");
    box.textContent = text || "";
    box.hidden = !text;
  }

  // Locate me: the browser's position, then the nearest postcode from postcodes.io
  function locate() {
    showError(null);
    if (!navigator.geolocation) { showError("Your browser cannot share your location. Please use Edit."); return; }
    const button = sheet.querySelector("[data-loc-locate]");
    button.disabled = true;
    navigator.geolocation.getCurrentPosition(async (pos) => {
      try {
        const { latitude, longitude } = pos.coords;
        const r = await fetch(`https://api.postcodes.io/postcodes?lon=${longitude}&lat=${latitude}&limit=1`);
        const found = ((await r.json()).result || [])[0];
        if (!found) throw new Error("none");
        if (typeof opts.onLocate === "function") {
          opts.onLocate({ postcode: found.postcode, area: found.admin_ward || found.admin_district || "" });
        }
        close();
      } catch (e) {
        showError("We could not find a UK postcode near you. Please use Edit.");
      } finally {
        button.disabled = false;
      }
    }, () => {
      button.disabled = false;
      showError("Location is turned off for this site. Please use Edit.");
    }, { timeout: 10000 });
  }

  function drawMap() {
    const box = sheet.querySelector(".loc-sheet__map");
    if (!window.L) { box.hidden = true; return; }
    box.hidden = false;
    if (!map) {
      map = L.map(box, {
        zoomControl: false, scrollWheelZoom: false, dragging: true, touchZoom: true,
        doubleClickZoom: true, boxZoom: false, keyboard: false, tap: false, zoomSnap: 0.25,
      });
      map.attributionControl.setPrefix(false);
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 18,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).addTo(map);
    }
    const centre = opts.centre;
    // A view first: a circle cannot be drawn on a map that has none yet
    map.setView(centre || (opts.dots && opts.dots[0] ? opts.dots[0].at : [51.515, -0.09]), centre ? 13 : 11);
    if (layer) layer.remove();
    layer = L.featureGroup().addTo(map);
    if (centre) {
      if (opts.miles) {
        L.circle(centre, { radius: opts.miles * MILE, color: "#1f7a4a", weight: 2, fillColor: "#1f7a4a", fillOpacity: 0.12 }).addTo(layer);
      }
      L.circleMarker(centre, { radius: 9, color: "#ffffff", weight: 3, fillColor: "#1f7a4a", fillOpacity: 1 }).addTo(layer);
    }
    (opts.dots || []).forEach((d) => {
      L.circleMarker(d.at, { radius: 7, color: "#ffffff", weight: 2, fillColor: "#e0572f", fillOpacity: 1 })
        .bindPopup(d.html).addTo(layer);
    });
    map.invalidateSize();
    if (layer.getLayers().length) {
      const bounds = layer.getBounds();
      if (bounds.getNorthEast().equals(bounds.getSouthWest())) map.setView(bounds.getCenter(), 13);
      else map.fitBounds(bounds, { padding: [28, 28], maxZoom: 14 });
    } else {
      map.setView([51.515, -0.09], 10); // London
    }
  }

  function open(options) {
    opts = options || {};
    if (!sheet) build();
    lastFocus = document.activeElement;
    sheet.querySelector("#loc-title").textContent = opts.title || "Choose a location";
    sheet.querySelector("[data-loc-place]").textContent = opts.place || "No location chosen";
    sheet.querySelector("[data-loc-radius]").textContent = opts.miles ? `Within ${opts.miles} ${opts.miles === 1 ? "mile" : "miles"}` : "";
    sheet.querySelector("[data-loc-edit-label]").textContent = opts.editLabel || "Postcode or area";
    const input = sheet.querySelector("[data-loc-input]");
    input.value = opts.editValue || "";
    input.placeholder = opts.editPlaceholder || "E8 1AB or Hackney";
    const radiusField = sheet.querySelector("[data-loc-radius-field]");
    radiusField.hidden = !opts.radiusOptions;
    if (opts.radiusOptions) {
      sheet.querySelector("[data-loc-radius-select]").innerHTML = opts.radiusOptions
        .map((m) => `<option value="${m}"${m === opts.radiusValue ? " selected" : ""}>Within ${m} ${m === 1 ? "mile" : "miles"}</option>`).join("");
    }
    const list = sheet.querySelector("[data-loc-suggest]");
    const suggestions = (opts.suggestions || []).filter(Boolean);
    sheet.querySelector("[data-loc-suggest-box]").hidden = !suggestions.length;
    list.innerHTML = suggestions.map((s) => `<li><button type="button" data-loc-pick="${esc(s)}"><img src="assets/icons/search-field.svg" alt="" width="20" height="20"><span>${esc(s)}</span></button></li>`).join("");
    toggleEdit(false);
    showError(null);
    sheet.hidden = false;
    document.body.classList.add("loc-open");
    requestAnimationFrame(() => {
      sheet.classList.add("is-open");
      drawMap();
      setTimeout(drawMap, 260); // after the slide in, when the size is final
      sheet.querySelector(".loc-sheet__close").focus();
    });
  }

  function close() {
    if (!sheet || sheet.hidden) return;
    sheet.classList.remove("is-open");
    document.body.classList.remove("loc-open");
    setTimeout(() => { sheet.hidden = true; }, 200);
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  window.QVLocation = { open, close };
})();
