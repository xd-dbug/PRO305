const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:3000/";

const TOKEN_KEY = "authToken";
const USER_ID_KEY = "authUserId";

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

export function getUserId() {
  return localStorage.getItem(USER_ID_KEY);
}

export function setUserId(userId) {
  if (userId) {
    localStorage.setItem(USER_ID_KEY, userId);
  } else {
    localStorage.removeItem(USER_ID_KEY);
  }
}

async function request(path, options = {}) {
  const token = getToken();

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });
  } catch {
    // fetch() throws a plain "Failed to fetch" TypeError when it can't even
    // reach the server (wrong URL, server not running, CORS, offline, etc.) —
    // that's not the same as the request reaching the API and failing.
    throw new Error(
      `Couldn't reach the API at ${API_BASE_URL}. Check that VITE_API_BASE_URL ` +
        `in your .env points to a running server and that it's reachable.`
    );
  }

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

export function register(email, password, displayName) {
  return request("auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, displayName }),
  });
}

export async function login(email, password) {
  const res = await request("auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setToken(res.token);
  setUserId(res.userId);
  return res;
}

// Contract: POST /mealplan/generate  { "preferences": { days, mealsPerDay } } -> 202 { jobId, status: "pending" }
export function generateMealPlan(preferences) {
  return request("mealplan/generate", {
    method: "POST",
    body: JSON.stringify({ preferences }),
  });
}

// Contract: GET /mealplan/status/{jobId} -> { jobId, status, mealPlan }
export function getMealPlanStatus(jobId) {
  return request(`mealplan/status/${jobId}`);
}