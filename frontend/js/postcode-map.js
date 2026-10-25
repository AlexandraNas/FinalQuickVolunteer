/* QuickVolunteer · location button under the postcode field
   Members type only a postcode. The name of the area (for example "Hackney Central")
   is worked out from it with postcodes.io and saved in the hidden area field; other
   members see that name, never the postcode. Without internet the first part of the
   postcode (for example "E8") is saved instead.
   Under the field a pin button shows the area; clicking it opens the
   "Choose a location" panel (js/location-sheet.js) with the map:
   - Onboarding and My profile: the circle is how far the member is happy to travel.
   - Post a request: the dot is the approximate area of the task. */
(function () {
  "use strict";
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

    // Pin button, placed under the row that holds the postcode
    const row = postcode.closest(".field-row") || postcode.closest(".field");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "loc-chip";
    button.hidden = true;
    button.innerHTML = '<span class="loc-chip__icon"><img src="assets/icons/pin.svg" alt="" width="18" height="18"></span>' +
      '<span class="loc-chip__text"><span class="loc-chip__place"></span><span class="loc-chip__radius"></span></span>' +
      '<span class="loc-chip__map">Map</span>';
    button.setAttribute("aria-label", "Show the area on a map");
    row.insertAdjacentElement("afterend", button);
    const placeEl = button.querySelector(".loc-chip__place");
    const radiusEl = button.querySelector(".loc-chip__radius");

    let typedPostcode = false; // the member changed the postcode themselves

    const miles = () => {
      if (!ids.distance) return null;
      const picked = document.querySelector(`[name="${ids.distance}"]:checked`);
      return picked ? Number(picked.value) : 1;
    };
    const placeName = (district) => {
      const name = area.value.trim();
      return name && name !== district ? `${name}, ${district}` : district;
    };

    function label(district) {
      placeEl.textContent = placeName(district);
      const m = miles();
      radiusEl.textContent = m ? `Within ${m} ${m === 1 ? "mile" : "miles"}` : "";
    }

    // Saved profiles keep their area name until the member changes the postcode.
    async function fillArea(value, district) {
      if (!typedPostcode && area.value.trim()) { label(district); return; }
      area.value = district;               // straight away, works offline
      label(district);
      try {
        const asked = clean(value);
        const r = await fetch(`https://api.postcodes.io/postcodes/${encodeURIComponent(asked)}`);
        if (!r.ok) return;
        const result = (await r.json()).result || {};
        const name = result.admin_ward || result.admin_district || "";
        if (name && clean(postcode.value) === asked) {
          area.value = name;
          label(district);
        }
      } catch (e) { /* offline: keep the postcode area, for example "E8" */ }
    }

    function update() {
      const value = postcode.value;
      if (!isFullPostcode(value)) { button.hidden = true; return; }
      const district = districtOf(value);
      button.hidden = false;
      fillArea(value, district);
    }

    function setPostcode(value) {
      postcode.value = clean(value);
      typedPostcode = true;
      postcode.dispatchEvent(new Event("input", { bubbles: true }));
      postcode.dispatchEvent(new Event("change", { bubbles: true }));
    }

    button.addEventListener("click", () => {
      if (!window.QVLocation) return;
      const district = districtOf(postcode.value);
      const options = Array.from(document.querySelectorAll(`[name="${ids.distance}"]`)).map((r) => Number(r.value));
      window.QVLocation.open({
        title: ids.distance ? "Your area" : "Area of the task",
        place: placeName(district),
        centre: (window.QV_DISTRICTS || {})[district] || null,
        miles: miles(),
        editLabel: "Postcode",
        editPlaceholder: "E8 1AB",
        editValue: postcode.value,
        radiusOptions: ids.distance && options.length ? options : null,
        radiusValue: miles(),
        onApply: ({ value, miles: m }) => {
          if (value && clean(value) !== clean(postcode.value)) setPostcode(value);
          if (ids.distance && m) {
            const radio = document.querySelector(`[name="${ids.distance}"][value="${m}"]`);
            if (radio) { radio.checked = true; radio.dispatchEvent(new Event("change", { bubbles: true })); }
          }
        },
        onLocate: ({ postcode: found }) => setPostcode(found),
      });
    });

    postcode.addEventListener("input", () => { typedPostcode = true; update(); });
    postcode.addEventListener("change", update);
    if (ids.distance) {
      document.querySelectorAll(`[name="${ids.distance}"]`).forEach((r) => r.addEventListener("change", update));
    }
    // Saved profiles are filled in after the page loads
    update();
    if (window.QV && window.QV.ready) window.QV.ready.then(update);
    window.addEventListener("load", update);
  }

  function start() { FIELDS.forEach(setUp); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
