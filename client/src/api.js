const BASE = import.meta.env.VITE_API_URL ?? "";
const KEY = import.meta.env.VITE_API_KEY ?? "";

export async function post(path, body) {
  return fetch(`${BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${KEY}`,
    },
    body: JSON.stringify(body),
  });
}

export async function get(path, body) {
  return fetch(`${BASE}${path}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${KEY}`,
    },
    body: JSON.stringify(body),
  });
}
