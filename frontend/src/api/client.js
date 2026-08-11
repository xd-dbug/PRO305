const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:3000/";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const message = body?.message || body?.error || `Request failed with ${response.status}`;
    throw new Error(message);
  }
  return body;
}

export function listRecipes() {
  return request("recipes");
}

export function getRecipe(id) {
  return request(`recipes/${id}`);
}

export function createRecipe(recipe) {
  return request("recipes", { method: "POST", body: JSON.stringify(recipe) });
}

export function updateRecipe(id, recipe) {
  return request(`recipes/${id}`, { method: "PUT", body: JSON.stringify(recipe) });
}

export function deleteRecipe(id) {
  return request(`recipes/${id}`, { method: "DELETE" });
}

export function rateRecipe(id, rating) {
  return request(`recipes/${id}/rate`, { method: "POST", body: JSON.stringify({ rating }) });
}

export function saveRecipe(id) {
  return request(`recipes/${id}/save`, { method: "POST" });
}

export function login(email, password) {
  return request("auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
}
