(function () {
    "use strict";

    function initializeDeadDropMap() {
        const mapElement = document.getElementById("dead-drop-map");
        const markerDataElement = document.getElementById("dead-drop-map-markers");

        if (!mapElement || !markerDataElement || typeof L === "undefined") {
            return;
        }

        let markers;
        try {
            markers = JSON.parse(markerDataElement.textContent);
        } catch (error) {
            console.error("Data marker Dead Drop tidak dapat dibaca.", error);
            return;
        }

        const defaultCenter = [-6.2, 106.816666];
        const map = L.map(mapElement).setView(defaultCenter, 12);

        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            referrerPolicy: "strict-origin-when-cross-origin",
            attribution:
                '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        }).addTo(map);

        const bounds = L.latLngBounds([]);

        markers.forEach(function (listing) {
            const latitude = Number(listing.latitude);
            const longitude = Number(listing.longitude);

            if (
                !Number.isFinite(latitude) ||
                !Number.isFinite(longitude) ||
                latitude < -90 ||
                latitude > 90 ||
                longitude < -180 ||
                longitude > 180
            ) {
                return;
            }

            const marker = L.marker([latitude, longitude]).addTo(map);
            const popup = document.createElement("div");
            const foodName = document.createElement("strong");
            foodName.textContent = listing.food_name;
            popup.appendChild(foodName);

            const location = document.createElement("p");
            location.textContent = listing.pickup_location;
            popup.appendChild(location);

            marker.bindPopup(popup);
            bounds.extend([latitude, longitude]);
        });

        if (bounds.isValid()) {
            map.fitBounds(bounds, { padding: [24, 24], maxZoom: 15 });
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initializeDeadDropMap);
    } else {
        initializeDeadDropMap();
    }
})();
