// Mocks the async meal-plan job described in API_CONTRACT.md
// (POST /mealplan/generate, GET /mealplan/status/{jobId}) until the real
// SQS-backed pipeline exists. Response shapes match the contract exactly, so
// swapping client.js's generateMealPlan/getMealPlanStatus to real `request()`
// calls later is a drop-in change — nothing calling them needs to change.

const jobs = new Map();

function makeJobId() {
  return `job_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function buildMockMealPlan(preferences) {
  const days = Number(preferences?.days) || 7;
  const mealsPerDay = Number(preferences?.mealsPerDay) || 3;
  const mealSlots = ["Breakfast", "Lunch", "Dinner", "Snack"];

  return {
    days: Array.from({ length: days }, (_, dayIdx) => ({
      day: dayIdx + 1,
      meals: Array.from({ length: mealsPerDay }, (_, mealIdx) => ({
        recipeId: null,
        name: `${mealSlots[mealIdx % mealSlots.length]} idea #${dayIdx * mealsPerDay + mealIdx + 1}`,
        notes: "Mock meal — replace once /mealplan/generate is live.",
      })),
    })),
  };
}

// Response 202: { jobId, status: "pending" }
export function generateMealPlanMock(preferences, { simulateFailure = false } = {}) {
  const jobId = makeJobId();
  jobs.set(jobId, {
    status: "pending",
    createdAt: Date.now(),
    resolveAfterMs: 6000 + Math.random() * 4000, // pretend the worker takes 6-10s
    simulateFailure,
    preferences,
  });
  return Promise.resolve({ jobId, status: "pending" });
}

export function getMealPlanStatusMock(jobId) {
  const job = jobs.get(jobId);
  if (!job) {
    return Promise.reject(new Error("Unknown job id"));
  }

  const elapsed = Date.now() - job.createdAt;
  if (elapsed < job.resolveAfterMs) {
    return Promise.resolve({ jobId, status: "pending", mealPlan: null });
  }

  if (job.status === "pending") {
    job.status = job.simulateFailure ? "failed" : "complete";
    job.mealPlan = job.status === "complete" ? buildMockMealPlan(job.preferences) : null;
  }

  if (job.status === "failed") {
    return Promise.resolve({ jobId, status: "failed", mealPlan: null });
  }

  return Promise.resolve({ jobId, status: "complete", mealPlan: job.mealPlan });
}
