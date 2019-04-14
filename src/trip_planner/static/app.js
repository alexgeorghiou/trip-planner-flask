// Progressive enhancement for the itinerary pages: HTMX error swaps and the Leaflet map.
(function () {
  "use strict";

  var DAY_COLOURS = ["#2563eb", "#db2777", "#059669", "#d97706", "#7c3aed", "#0891b2", "#dc2626"];

  document.addEventListener("htmx:beforeSwap", function (evt) {
    // Validation / conflict responses carry a re-rendered fragment with the error message.
    var status = evt.detail.xhr.status;
    if (status === 409 || status === 422) {
      evt.detail.shouldSwap = true;
      evt.detail.isError = false;
    }
  });

  function drawMap(map, layer, data) {
    layer.clearLayers();
    var bounds = [];
    data.days.forEach(function (day, i) {
      var colour = DAY_COLOURS[i % DAY_COLOURS.length];
      var latlngs = day.stops.map(function (s) { return [s.lat, s.lon]; });
      day.stops.forEach(function (stop, j) {
        L.circleMarker([stop.lat, stop.lon], { radius: 7, color: colour, weight: 2, fillOpacity: 0.85 })
          .bindTooltip("Day " + day.number + " · " + (j + 1) + ". " + stop.name)
          .addTo(layer);
      });
      if (latlngs.length > 1) {
        L.polyline(latlngs, { color: colour, weight: 3, opacity: 0.7, dashArray: "6 6" }).addTo(layer);
      }
      bounds = bounds.concat(latlngs);
    });
    if (bounds.length) {
      map.fitBounds(bounds, { padding: [24, 24], maxZoom: 15 });
    }
  }

  function initMap() {
    var el = document.getElementById("map");
    if (!el || typeof L === "undefined") return;
    var map = L.map(el, { scrollWheelZoom: false }).setView([20, 0], 2);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);
    var layer = L.layerGroup().addTo(map);

    var inline = document.getElementById("map-data");
    if (inline) {
      drawMap(map, layer, JSON.parse(inline.textContent));
      return;
    }
    var src = el.dataset.src;
    if (!src) return;
    var refresh = function () {
      fetch(src, { headers: { Accept: "application/json" } })
        .then(function (r) { return r.json(); })
        .then(function (data) { drawMap(map, layer, data); })
        .catch(function () { /* the map is decorative; the itinerary still works */ });
    };
    refresh();
    document.body.addEventListener("itinerary-changed", refresh);
  }

  document.addEventListener("DOMContentLoaded", initMap);
})();
