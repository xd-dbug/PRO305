import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { deleteRecipe, getRecipe, getUserId, rateRecipe, getToken } from "./api/client";
import "./Recipe.css";

function AuthorActions({ recipeId }) {
  const navigate = useNavigate();
  const [confirming, setConfirming] = useState(false);
  const [status, setStatus] = useState("idle"); // idle | deleting | error
  const [error, setError] = useState(null);

  async function handleDelete() {
    setStatus("deleting");
    setError(null);
    try {
      await deleteRecipe(recipeId);
      navigate("/recipes");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }

  return (
    <div className="author-actions">
      <Link to={`/recipes/${recipeId}/edit`} className="edit-link">
        Edit
      </Link>
      {!confirming ? (
        <button type="button" className="delete-btn" onClick={() => setConfirming(true)}>
          Delete
        </button>
      ) : (
        <span className="delete-confirm">
          Delete this recipe?
          <button type="button" className="delete-confirm-btn" onClick={handleDelete} disabled={status === "deleting"}>
            {status === "deleting" ? "Deleting…" : "Yes, delete"}
          </button>
          <button type="button" className="delete-cancel-btn" onClick={() => setConfirming(false)} disabled={status === "deleting"}>
            Cancel
          </button>
        </span>
      )}
      {status === "error" && <span className="rating-widget-status error">{error}</span>}
    </div>
  );
}

function RatingWidget({ recipeId, onRated }) {
  const [hoverScore, setHoverScore] = useState(0);
  const [myScore, setMyScore] = useState(0);
  const [status, setStatus] = useState("idle"); // idle | submitting | error
  const [error, setError] = useState(null);

  if (!getToken()) {
    return (
      <p className="rating-widget-message">
        <Link to="/login">Log in</Link> to rate this recipe.
      </p>
    );
  }

  async function submitScore(score) {
    setStatus("submitting");
    setError(null);
    try {
      const res = await rateRecipe(recipeId, score);
      setMyScore(score);
      setStatus("idle");
      onRated(res.avgRating);
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }

  const displayScore = hoverScore || myScore;

  return (
    <div className="rating-widget">
      <div className="rating-widget-stars" onMouseLeave={() => setHoverScore(0)}>
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            className={`star-button${n <= displayScore ? " filled" : ""}`}
            onMouseEnter={() => setHoverScore(n)}
            onClick={() => submitScore(n)}
            disabled={status === "submitting"}
            aria-label={`Rate ${n} star${n > 1 ? "s" : ""}`}
          >
            ★
          </button>
        ))}
      </div>
      {status === "submitting" && <span className="rating-widget-status">Submitting…</span>}
      {status === "error" && <span className="rating-widget-status error">{error}</span>}
      {myScore > 0 && status === "idle" && (
        <span className="rating-widget-status">You rated this {myScore}★</span>
      )}
    </div>
  );
}

function Recipe() {
  const { recipeId } = useParams();
  const [recipe, setRecipe] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    getRecipe(recipeId)
      .then((data) => {
        if (cancelled) return;
        setRecipe(data);
        setStatus("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message);
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [recipeId]);

  function handleRated(newAvgRating) {
    setRecipe((prev) => (prev ? { ...prev, avgRating: newAvgRating } : prev));
  }

  if (status === "loading") {
    return (
      <div className="recipe-page">
        <div className="recipe-content">
          <p className="state-message">Loading recipe…</p>
        </div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="recipe-page">
        <div className="recipe-content">
          <p className="state-message error">Couldn't load this recipe: {error}</p>
          <Link to="/recipe">← All recipes</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="recipe-page">
      <article className="recipe-content">
        <Link to="/recipe" className="back-link">
          ← All recipes
        </Link>

        <header className="recipe-title-bar">
          <h1>{recipe.title}</h1>
          <div className="recipe-title-meta">
            <span className="recipe-rating">
              ★ {typeof recipe.avgRating === "number" ? recipe.avgRating.toFixed(1) : "Not yet rated"}
            </span>
            {recipe.tags?.length > 0 && (
              <ul className="tag-list">
                {recipe.tags.map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
            )}
            <RatingWidget recipeId={recipeId} onRated={handleRated} />
          </div>
        </header>

        {recipe.authorId === getUserId() && <AuthorActions recipeId={recipeId} />}

        {/* servings/prepTime/cookTime aren't in API_CONTRACT.md yet — they'll
            show as "—" until Person A adds them to the recipe schema. */}
        <div className="recipe-meta-row">
          <div className="meta-item">
            <span className="meta-label">Servings</span>
            <span className="meta-value">{recipe.servings ?? "—"}</span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Prep time</span>
            <span className="meta-value">{recipe.prepTime ?? "—"}</span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Cook time</span>
            <span className="meta-value">{recipe.cookTime ?? "—"}</span>
          </div>
        </div>

        <div className="recipe-layout">
          <div className="recipe-layout-left">
            <section className="recipe-box ingredients-box">
              <h2>Ingredients</h2>
              <ul className="ingredient-list">
                {recipe.ingredients.map((ing, i) => (
                  <li key={i}>
                    <span className="amount">{ing.amount}</span>
                    {ing.name}
                  </li>
                ))}
              </ul>
            </section>

            {/* notes isn't in API_CONTRACT.md yet either — see comment above. */}
            <section className="recipe-box notes-box">
              <h2>Notes</h2>
              <p className="notes-text">{recipe.notes || "No notes yet."}</p>
            </section>
          </div>

          <div className="recipe-layout-right">
            <section className="recipe-box directions-box">
              <h2>Directions</h2>
              <ol className="step-list">
                {recipe.steps.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            </section>

            <section className="recipe-box photo-box">
              {recipe.photoUrl ? (
                <img src={recipe.photoUrl} alt={recipe.title} className="photo-box-img" />
              ) : (
                <div className="photo-box-placeholder" aria-hidden="true">
                  🍽️
                </div>
              )}
            </section>
          </div>
        </div>
      </article>
    </div>
  );
}

export default Recipe;