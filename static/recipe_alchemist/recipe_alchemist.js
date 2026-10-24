// Simpan resep Spoonacular tanpa memuat ulang halaman.
// Tanpa JavaScript, form tetap bekerja lewat POST biasa + redirect.
document.addEventListener("submit", async (event) => {
  const form = event.target;
  if (!form.matches("[data-ra-save]")) return;
  event.preventDefault();

  const button = form.querySelector("button");
  button.disabled = true;
  try {
    const response = await fetch(form.action, {
      method: "POST",
      headers: { "X-Requested-With": "XMLHttpRequest" },
      body: new FormData(form), // sudah memuat csrfmiddlewaretoken
    });
    const data = await response.json();
    if (response.status === 401) {
      // Belum masuk / sesi habis: ke halaman masuk lalu kembali ke halaman ini (sama seperti Death Clock).
      const next = encodeURIComponent(location.pathname + location.search);
      window.location.href = `${data.login_url || "/login/"}?next=${next}`;
      return;
    }
    if (!response.ok) throw new Error(data.detail || "Gagal menyimpan.");
    form.outerHTML = `<a class="pn-badge pn-tone-hex" href="${data.url}">Tersimpan ✓ Lihat</a>`;
  } catch (error) {
    button.disabled = false;
    button.textContent = error.message || "Gagal menyimpan. Coba lagi.";
  }
});