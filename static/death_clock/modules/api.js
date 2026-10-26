/* Komunikasi dengan server: fetch + header AJAX + CSRF, dan jenis galat yang dipakai modul lain. */

export class RequestError extends Error {}

/** Sesi habis: halaman sedang diarahkan ke /login/, jadi galat ini tidak perlu ditampilkan. */
export class Redirecting extends Error {}

const DEFAULT_ERROR = "Gagal terhubung ke server. Coba lagi sebentar.";

/**
 * Buat fungsi ``send(url, { method, body, signal })`` yang mengembalikan ``{ response, data }``.
 * ``data`` adalah JSON dari server (objek kosong bila respons bukan JSON).
 */
export function createClient(csrfToken) {
  return async function send(url, { method = "GET", body, signal } = {}) {
    const headers = { "X-Requested-With": "XMLHttpRequest", Accept: "application/json" };
    if (method !== "GET") headers["X-CSRFToken"] = csrfToken;
    const response = await fetch(url, { method, body, signal, headers, credentials: "same-origin" });
    let data = {};
    try {
      data = await response.json();
    } catch (_) {
      /* respons bukan JSON, mis. halaman error */
    }
    if (response.status === 401) {
      window.location.href = `${data.login_url || "/login/"}?next=${encodeURIComponent(location.pathname)}`;
      throw new Redirecting();
    }
    return { response, data };
  };
}

/** Lempar RequestError berisi pesan server (mis. 429 "Terlalu banyak permintaan") bila respons gagal. */
export function ensureOk({ response, data }, fallback = DEFAULT_ERROR) {
  if (!response.ok) throw new RequestError(data.detail || fallback);
  return data;
}

/** Pesan yang layak ditampilkan untuk sebuah galat, atau null bila galat itu disengaja (batal/redirect). */
export function errorMessage(error) {
  if (error && (error.name === "AbortError" || error instanceof Redirecting)) return null;
  return (error instanceof RequestError && error.message) || DEFAULT_ERROR;
}
