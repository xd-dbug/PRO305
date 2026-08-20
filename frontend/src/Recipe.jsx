import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getRecipe } from "./api/client";
import "./Recipe.css";

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
          </div>
        </header>

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