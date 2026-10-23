/* QuickVolunteer · area map under the postcode field
   Shows a circle for the area of the postcode, never the exact address:
   - Onboarding and My profile: the circle is how far the member is happy to travel.
   - Post a request: the circle is the approximate area of the task.
   Members type only a postcode. The name of the area (for example "Hackney Central")
   is worked out from it with postcodes.io and saved in the hidden area field; other
   members see that name, never the postcode. Without internet the first part of the
   postcode (for example "E8") is saved instead, and the map stays hidden. */
(function () {
  "use strict";
  const MILE = 1609.34;
  const FIELDS = [
    { postcode: "postcode", area: "area", distance: "distance" },     // onboarding, profile
    { postcode: "req-postcode", area: "req-area", distance: null },   // post a request
  ];

  function clean(value) {
    return String(value || "").toUpperCase().replace(/\s+/g, " ").trim();
  }
  function isFullPostcode(value) {
    return /^[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}$/.test(clean(value));
  }
  function districtOf(value) {
    const v = clean(value).replace(/\s/g, "");
    return v.length > 3 ? v.slice(0, v.length - 3) : v;
  }

  function setUp(ids) {
    const postcode = document.getElementById(ids.postcode);
    const area = document.getElementById(ids.area);
    if (!postcode || !area) return;
    const canMap = !!window.L;

    // Map box, placed under the postcode field
    const row = postcode.closest(".field-row") || postcode.closest(".field");
    const box = document.createElement("figure");
    box.className = "area-map";
    box.hidden = true;
    box.innerHTML = '<div class="area-map__map" role="img" aria-label="Map of the area around your postcode"></div>' +
      '<figcaption class="area-map__note" aria-live="polite"></figcaption>';
    row.insertAdjacentElement("afterend", box);
    const note = box.querySelector(".area-map__note");

    let map = null;
    let circle = null;
    let lastDistrict = "";
    let typedPostcode = false; // the member changed the postcode themselves

    function radius() {
      if (!ids.distance) return 800; // a task: about half a mile around the area
      const picked = document.querySelector(`[name="${ids.distance}"]:checked`);
      return (picked ? Number(picked.value) : 1) * MILE;
    }

    function caption(district) {
      const name = area.value.trim();
      note.textContent = name && name !== district ? `${name}, ${district}` : district;
    }

    function draw(lat, lng, district) {
      if (!canMap) { box.hidden = true; return; }
      box.hidden = false;
      if (!map) {
        map = L.map(box.querySelector(".area-map__map"), {
          zoomControl: true, scrollWheelZoom: false, dragging: !L.Browser.mobile, tap: false,
        });
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 18,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        }).addTo(map);
      }
      map.setView([lat, lng], 13);
      if (circle) circle.remove();
      circle = L.circle([lat, lng], {
        radius: radius(), color: "#166a3e", weight: 2, fillColor: "#166a3e", fillOpacity: 0.15,
      }).addTo(map);
      map.invalidateSize();
      map.fitBounds(circle.getBounds(), { padding: [12, 12] });
      caption(district);
    }

    // Saved profiles keep their area name until the member changes the postcode.
    async function fillArea(value, district) {
      if (!typedPostcode && area.value.trim()) return;
      area.value = district;               // straight away, works offline
      caption(district);
      try {
        const asked = clean(value);
        const r = await fetch(`https://api.postcodes.io/postcodes/${encodeURIComponent(asked)}`);
        if (!r.ok) return;
        const result = (await r.json()).result || {};
        const name = result.admin_ward || result.admin_district || "";
        if (name && clean(postcode.value) === asked) {
          area.value = name;
          caption(district);
        }
      } catch (e) { /* offline: keep the postcode area, for example "E8" */ }
    }

    function update() {
      const value = postcode.value;
      if (!isFullPostcode(value)) { box.hidden = true; return; }
      const district = districtOf(value);
      const centre = (window.QV_DISTRICTS || {})[district];
      if (!centre) { box.hidden = true; fillArea(value, district); return; }
      lastDistrict = district;
      draw(centre[0], centre[1], district);
      fillArea(value, district);
    }

    postcode.addEventListener("input", () => { typedPostcode = true; update(); });
    postcode.addEventListener("change", update);
    if (ids.distance) {
      document.querySelectorAll(`[name="${ids.distance}"]`).forEach((r) => r.addEventListener("change", update));
    }
    // Saved profiles are filled in after the page loads
    update();
    if (window.QV && window.QV.ready) window.QV.ready.then(update);
    window.addEventListener("load", update);
    // Onboarding shows the area step later: redraw when it becomes visible
    if ("IntersectionObserver" in window) {
      new IntersectionObserver((entries) => {
        if (entries.some((e) => e.isIntersecting) && map) { map.invalidateSize(); if (circle) map.fitBounds(circle.getBounds(), { padding: [12, 12] }); }
      }).observe(box);
    }
  }

  function start() { FIELDS.forEach(setUp); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
