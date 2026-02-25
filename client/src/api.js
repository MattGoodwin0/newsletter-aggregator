// In dev, Vite proxies /api → localhost:5000
// In production (Vercel), calls go to the Railway backend via VITE_API_URL
const BASE = import.meta.env.VITE_API_URL ?? "";

export async function post(path, body) {
  return fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
