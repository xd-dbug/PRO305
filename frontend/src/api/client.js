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

// Thrown by request() for every failure case — network-level (couldn't reach
// the server at all) and HTTP-level (server responded with an error status).
// `status` is 0 for network failures (never reached the server) so it's always
// safe to check `err.status`, and `code` is the contract's `error` field
// (e.g. "Unauthorized") when the server sent one.
export class ApiError extends Error {
  constructor(message, { status = 0, code = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

// Maps a caught error to user-facing copy, with per-call overrides for
// statuses that need different wording in different flows (e.g. a 401 on
// login means "wrong password", but a 401 on create-recipe means "log in
// first"). Falls back to the API's own message for anything not covered.
export function friendlyApiErrorMessage(err, overrides = {}) {
  const status = err instanceof ApiError ? err.status : null;
  if (status !== null && overrides[status]) return overrides[status];

  switch (status) {
    case 0:
      return err.message; // already a clear "couldn't reach the API" message
    case 401:
      return "You need to be logged in to do that.";
    case 403:
      return "You don't have permission to do that.";
    case 404:
      return "That couldn't be found.";
    default:
      if (status >= 500) {
        return "Something went wrong on our end. Please try again in a moment.";
      }
      return err.message || "Something went wrong.";
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
    throw new ApiError(
      `Couldn't reach the API at ${API_BASE_URL}. Check that VITE_API_BASE_URL ` +
        `in your .env points to a running server and that it's reachable.`,
      { status: 0, code: "network_error" }
    );
  }

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const message = body?.message || body?.error || `Request failed with ${response.status}`;
    throw new ApiError(message, { status: response.status, code: body?.error ?? null });
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