const BASE = import.meta.env.VITE_API_URL ?? "";

export async function post(path, body) {
  const { token } = await fetch(`${BASE}/api/csrf-token`).then((r) => r.json());

  return fetch(`${BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": token,
    },
    body: JSON.stringify(body),
  });
}

export async function get(path, body) {
  const { token } = await fetch(`${BASE}/api/csrf-token`).then((r) => r.json());

  return fetch(`${BASE}${path}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": token,
    },
    body: JSON.stringify(body),
  });
}
