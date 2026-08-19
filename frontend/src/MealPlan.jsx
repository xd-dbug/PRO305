import { useEffect, useRef, useState } from "react";
import { generateMealPlan, getMealPlanStatus } from "./api/client";
import "./MealPlan.css";

const POLL_INTERVAL_MS = 4000;
const TIMEOUT_MS = 2 * 60 * 1000; // cap at ~2 min per API_CONTRACT.md

function MealPlan() {
  const [days, setDays] = useState(7);
  const [mealsPerDay, setMealsPerDay] = useState(3);
  const [simulateFailure, setSimulateFailure] = useState(false);

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
      const { jobId } = await generateMealPlan(
        { days: Number(days), mealsPerDay: Number(mealsPerDay) },
        { simulateFailure }
      );
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
        Queues a meal-plan job and polls for the result — the same flow the real
        SQS-backed pipeline will use once it's live.
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
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={simulateFailure}
            onChange={(e) => setSimulateFailure(e.target.checked)}
            disabled={isPending}
          />
          Simulate a failed job (dev)
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
                    <span className="meal-name">{meal.name}</span>
                    {meal.notes && <span className="meal-notes">{meal.notes}</span>}
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
