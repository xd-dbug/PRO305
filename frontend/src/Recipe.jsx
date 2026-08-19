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
    return <p className="state-message">Loading recipe…</p>;
  }

  if (status === "error") {
    return (
      <div className="recipe-page">
        <p className="state-message error">Couldn't load this recipe: {error}</p>
        <Link to="/recipe">← All recipes</Link>
      </div>
    );
  }

  return (
    <article className="recipe-page">
      <Link to="/recipe" className="back-link">
        ← All recipes
      </Link>

      <div className="recipe-hero">
        {recipe.photoUrl ? (
          <img src={recipe.photoUrl} alt={recipe.title} className="recipe-hero-photo" />
        ) : (
          <div className="recipe-hero-placeholder" aria-hidden="true">
            🍽️
          </div>
        )}
        <div>
          <h1>{recipe.title}</h1>
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
      </div>

      <div className="recipe-body">
        <section>
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

        <section>
          <h2>Steps</h2>
          <ol className="step-list">
            {recipe.steps.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
        </section>
      </div>
    </article>
  );
}

export default Recipe;