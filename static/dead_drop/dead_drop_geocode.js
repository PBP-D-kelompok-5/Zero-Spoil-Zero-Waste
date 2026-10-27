(function () {
    "use strict";

    document.addEventListener("click", async function (event) {
        const button = event.target.closest("#geocode-location");
        if (!button) return;

        const locationField = document.getElementById("id_pickup_location");
        const latitudeField = document.getElementById("id_latitude");
        const longitudeField = document.getElementById("id_longitude");
        const resultMessage = document.getElementById("geocode-result");

        if (!locationField || !latitudeField || !longitudeField || !resultMessage) return;

        const query = locationField.value.trim();
        if (!query) {
            resultMessage.textContent = "Masukkan nama atau alamat lokasi dulu.";
            return;
        }

        button.disabled = true;
        resultMessage.textContent = "Sedang mencari lokasi…";

        try {
            const url = new URL(button.dataset.geocodeUrl, window.location.origin);
            url.searchParams.set("q", query);
            const response = await fetch(url);
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Pencarian lokasi gagal.");

            latitudeField.value = data.latitude;
            longitudeField.value = data.longitude;
            resultMessage.textContent = `Koordinat ditemukan: ${data.display_name}`;
        } catch (error) {
            resultMessage.textContent = error.message;
        } finally {
            button.disabled = false;
        }
    });
})();
