import { generateMealPlanMock, getMealPlanStatusMock } from "./mealPlanMock";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:3000/";

const TOKEN_KEY = "authToken";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

async function request(path, options = {}) {
  const token = getToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
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

// GET /recipes?page=&limit=&tag=
export function listRecipes({ page = 1, limit = 20, tag } = {}) {
  const params = new URLSearchParams();
  params.set("page", page);
  params.set("limit", limit);
  if (tag) params.set("tag", tag);
  return request(`recipes?${params.toString()}`);
}

export function getRecipe(recipeId) {
  return request(`recipes/${recipeId}`);
}

// Body shape per contract: everything in GET /recipes/{id} minus recipeId/avgRating
export function createRecipe(recipe) {
  return request("recipes", { method: "POST", body: JSON.stringify(recipe) });
}

export function updateRecipe(recipeId, recipe) {
  return request(`recipes/${recipeId}`, { method: "PUT", body: JSON.stringify(recipe) });
}

export function deleteRecipe(recipeId) {
  return request(`recipes/${recipeId}`, { method: "DELETE" });
}

// Contract: POST /recipes/{recipeId}/ratings  { "score": number } -> { recipeId, avgRating }
export function rateRecipe(recipeId, score) {
  return request(`recipes/${recipeId}/ratings`, {
    method: "POST",
    body: JSON.stringify({ score }),
  });
}

// NOT in API_CONTRACT.md — there is no "save/bookmark a recipe" route defined for
// Person A's Recipes API yet. Left here so nothing that already calls it breaks,
// but it will 404 against the mock/real API until the contract is updated and
// signed off. Flag this to Person A before relying on it.
export function saveRecipe(recipeId) {
  return request(`recipes/${recipeId}/save`, { method: "POST" });
}

export function login(email, password) {
  return request("auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
}

// TODO(backend): the real pipeline (POST /mealplan/generate + SQS worker +
// GET /mealplan/status/{jobId}) doesn't exist yet. These two currently delegate
// to a local mock (see ./mealPlanMock.js) so the polling UI can be built and
// exercised end-to-end. Once the real endpoints are live, swap these bodies for:
//   generateMealPlan  -> request("mealplan/generate", { method: "POST", body: JSON.stringify({ preferences }) })
//   getMealPlanStatus -> request(`mealplan/status/${jobId}`)
// The response shapes already match the contract, so nothing calling these two
// functions needs to change.
export function generateMealPlan(preferences, opts) {
  return generateMealPlanMock(preferences, opts);
}

export function getMealPlanStatus(jobId) {
  return getMealPlanStatusMock(jobId);
}