import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  generateMealPlan,
  getMealPlanStatus,
  getPreferences,
  getToken,
  updatePreferences,
} from "./api/client";
import "./MealPlan.css";

const POLL_INTERVAL_MS = 4000;
const TIMEOUT_MS = 2 * 60 * 1000; // cap at ~2 min per API_CONTRACT.md

function parseDietaryTags(input) {
  return input
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
}

function MealPlan() {
  const navigate = useNavigate();
  const [days, setDays] = useState(7);
  const [mealsPerDay, setMealsPerDay] = useState(3);
  const [dietaryTagsInput, setDietaryTagsInput] = useState("");

  // idle | pending | complete | failed | timeout | error
  const [phase, setPhase] = useState("idle");
  const [mealPlan, setMealPlan] = useState(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [error, setError] = useState(null);

  // Tracks which job is "current" so a stale poll response (e.g. after a reset
  // or a resubmit) can't clobber newer state.
  const activeJobIdRef = useRef(null);
  const pollTimeoutRef = useRef(null);
  const tickIntervalRef = useRef(null);
  const startTimeRef = useRef(null);

  function clearTimers() {
    if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
    if (tickIntervalRef.current) clearInterval(tickIntervalRef.current);
    pollTimeoutRef.current = null;
    tickIntervalRef.current = null;
  }

  useEffect(() => clearTimers, []);

  // Pre-fill from the user's saved preferences, if any. Not critical to the
  // page working — if it fails (e.g. not logged in yet) the field just
  // starts empty, same as generating always did before this existed.
  useEffect(() => {
    if (!getToken()) return;
    getPreferences()
      .then((res) => setDietaryTagsInput((res.dietaryTags || []).join(", ")))
      .catch(() => {});
  }, []);

  function schedulePoll(jobId) {
    pollTimeoutRef.current = setTimeout(() => runPoll(jobId), POLL_INTERVAL_MS);
  }

  function runPoll(jobId) {
    if (activeJobIdRef.current !== jobId) return; // superseded

    if (Date.now() - startTimeRef.current > TIMEOUT_MS) {
      clearTimers();
      setPhase("timeout");
      return;
    }

    getMealPlanStatus(jobId)
      .then((res) => {
        if (activeJobIdRef.current !== jobId) return;

        if (res.status === "pending") {
          schedulePoll(jobId);
          return;
        }
        clearTimers();
        if (res.status === "complete") {
          setMealPlan(res.mealPlan);
          setPhase("complete");
        } else {
          setPhase("failed");
        }
      })
      .catch((err) => {
        if (activeJobIdRef.current !== jobId) return;
        clearTimers();
        setError(err.message);
        setPhase("error");
      });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    clearTimers();
    setError(null);
    setMealPlan(null);
    setElapsedMs(0);
    setPhase("pending");

    try {
      // Dietary tags are a property of the user's profile, not part of the
      // generate request itself — the mealplan consumer reads them straight
      // from the users/me/preferences table (backend/mealplan/queries.py).
      // Save whatever's in the field before generating so this run (and
      // future ones) picks it up.
      await updatePreferences(parseDietaryTags(dietaryTagsInput));

      const { jobId } = await generateMealPlan({
        days: Number(days),
        mealsPerDay: Number(mealsPerDay),
      });
      activeJobIdRef.current = jobId;
      startTimeRef.current = Date.now();

      tickIntervalRef.current = setInterval(() => {
        setElapsedMs(Date.now() - startTimeRef.current);
      }, 1000);

      schedulePoll(jobId);
    } catch (err) {
      setError(err.message);
      setPhase("error");
    }
  }

  // Hands off to RecipeCreate pre-filled with everything Claude generated
  // (see backend/mealplan/app.py's build_prompt) rather than posting
  // straight to POST /recipes, so the user can review/tweak before it's
  // actually saved.
  function handleSaveAsRecipe(meal) {
    navigate("/recipes/new", {
      state: {
        title: meal.name,
        notes: meal.notes || "",
        servings: meal.servings || "",
        prepTime: meal.prepTime || "",
        cookTime: meal.cookTime || "",
        ingredients: meal.ingredients || [],
        steps: meal.steps || [],
      },
    });
  }

  function handleReset() {
    activeJobIdRef.current = null;
    clearTimers();
    setPhase("idle");
    setMealPlan(null);
    setError(null);
  }

  const isPending = phase === "pending";

  return (
    <div className="mealplan-page">
      <h1>Meal plan</h1>
      <p className="mealplan-intro">
        Queues a meal-plan job and polls for the result.
      </p>

      <form className="mealplan-form" onSubmit={handleSubmit}>
        <label>
          Days
          <input
            type="number"
            min="1"
            max="14"
            value={days}
            onChange={(e) => setDays(e.target.value)}
            disabled={isPending}
          />
        </label>
        <label>
          Meals per day
          <input
            type="number"
            min="1"
            max="6"
            value={mealsPerDay}
            onChange={(e) => setMealsPerDay(e.target.value)}
            disabled={isPending}
          />
        </label>
        <label>
          Dietary preferences
          <input
            type="text"
            placeholder="vegetarian, gluten-free"
            value={dietaryTagsInput}
            onChange={(e) => setDietaryTagsInput(e.target.value)}
            disabled={isPending}
          />
        </label>

        <button type="submit" disabled={isPending}>
          {isPending ? "Generating…" : "Generate meal plan"}
        </button>
      </form>

      {phase === "pending" && (
        <div className="mealplan-status pending">
          <div className="spinner" aria-hidden="true" />
          <p>
            Job queued — polling every {POLL_INTERVAL_MS / 1000}s
            <span className="elapsed"> · {Math.floor(elapsedMs / 1000)}s elapsed</span>
          </p>
        </div>
      )}

      {phase === "timeout" && (
        <div className="mealplan-status timeout">
          <p>Still no result after 2 minutes. The job may have stalled.</p>
          <button onClick={handleReset}>Try again</button>
        </div>
      )}

      {phase === "failed" && (
        <div className="mealplan-status failed">
          <p>The meal-plan job failed. Nothing was generated.</p>
          <button onClick={handleReset}>Try again</button>
        </div>
      )}

      {phase === "error" && (
        <div className="mealplan-status failed">
          <p>Couldn't generate a meal plan: {error}</p>
          <button onClick={handleReset}>Try again</button>
        </div>
      )}

      {phase === "complete" && mealPlan && (
        <div className="mealplan-result">
          <button className="reset-btn" onClick={handleReset}>
            Generate another
          </button>
          {mealPlan.days.map((day) => (
            <div className="mealplan-day" key={day.day}>
              <h2>Day {day.day}</h2>
              <ul>
                {day.meals.map((meal, i) => (
                  <li key={i}>
                    <div className="meal-row">
                      <div className="meal-info">
                        <span className="meal-name">{meal.name}</span>
                        {meal.notes && <span className="meal-notes">{meal.notes}</span>}
                        {(meal.servings || meal.prepTime || meal.cookTime) && (
                          <span className="meal-meta">
                            {[
                              meal.servings && `Serves ${meal.servings}`,
                              meal.prepTime && `Prep ${meal.prepTime}`,
                              meal.cookTime && `Cook ${meal.cookTime}`,
                            ]
                              .filter(Boolean)
                              .join(" · ")}
                          </span>
                        )}
                      </div>
                      <button
                        type="button"
                        className="save-as-recipe-btn"
                        onClick={() => handleSaveAsRecipe(meal)}
                      >
                        Save as recipe
                      </button>
                    </div>
                    {(meal.ingredients?.length > 0 || meal.steps?.length > 0) && (
                      <details className="meal-details">
                        <summary>Ingredients &amp; steps</summary>
                        {meal.ingredients?.length > 0 && (
                          <ul className="meal-ingredients">
                            {meal.ingredients.map((ing, j) => (
                              <li key={j}>
                                {ing.amount} {ing.name}
                              </li>
                            ))}
                          </ul>
                        )}
                        {meal.steps?.length > 0 && (
                          <ol className="meal-steps">
                            {meal.steps.map((step, j) => (
                              <li key={j}>{step}</li>
                            ))}
                          </ol>
                        )}
                      </details>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default MealPlan;