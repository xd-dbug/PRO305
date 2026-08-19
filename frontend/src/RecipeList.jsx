import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { listRecipes } from "./api/client";
import "./RecipeList.css";

function RecipeList() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Number(searchParams.get("page")) || 1;
  const tag = searchParams.get("tag") || "";

  const [data, setData] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const [error, setError] = useState(null);
  const [tagInput, setTagInput] = useState(tag);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    listRecipes({ page, tag: tag || undefined })
      .then((res) => {
        if (cancelled) return;
        setData(res);
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
  }, [page, tag]);

  function applyTagFilter(e) {
    e.preventDefault();
    const next = { page: "1" };
    if (tagInput) next.tag = tagInput;
    setSearchParams(next);
  }

  function clearTagFilter() {
    setTagInput("");
    setSearchParams({ page: "1" });
  }

  function goToPage(nextPage) {
    const next = { page: String(nextPage) };
    if (tag) next.tag = tag;
    setSearchParams(next);
  }

  return (
    <div className="recipe-list-page">
      <div className="recipe-list-content">
      <header className="recipe-list-header">
        <h1>Recipes</h1>
        <Link to="/recipes/new" className="new-recipe-btn">
          + New recipe
        </Link>
      </header>

      <form className="tag-filter" onSubmit={applyTagFilter}>
        <input
          type="text"
          placeholder="Filter by tag (e.g. vegetarian)"
          value={tagInput}
          onChange={(e) => setTagInput(e.target.value)}
        />
        <button type="submit">Filter</button>
        {tag && (
          <button type="button" className="clear-filter" onClick={clearTagFilter}>
            Clear
          </button>
        )}
      </form>

      {status === "loading" && <p className="state-message">Loading recipes…</p>}

      {status === "error" && (
        <p className="state-message error">Couldn't load recipes: {error}</p>
      )}

      {status === "ready" && data.recipes.length === 0 && (
        <p className="state-message">
          No recipes {tag ? `tagged "${tag}"` : "yet"}.{" "}
          <Link to="/recipes/new">Add the first one</Link>.
        </p>
      )}

      {status === "ready" && data.recipes.length > 0 && (
        <>
          <ul className="recipe-grid">
            {data.recipes.map((recipe) => (
              <li className="recipe-card" key={recipe.recipeId}>
                <Link to={`/recipes/${recipe.recipeId}`}>
                  <div className="recipe-photo">
                    {recipe.photoUrl ? (
                      <img src={recipe.photoUrl} alt={recipe.title} />
                    ) : (
                      <div className="recipe-photo-placeholder" aria-hidden="true">
                        🍽️
                      </div>
                    )}
                  </div>
                  <h2>{recipe.title}</h2>
                  <span className="recipe-rating">
                    ★ {typeof recipe.avgRating === "number" ? recipe.avgRating.toFixed(1) : "—"}
                  </span>
                </Link>
              </li>
            ))}
          </ul>

          <nav className="pagination" aria-label="Recipe pages">
            <button disabled={data.page <= 1} onClick={() => goToPage(data.page - 1)}>
              Previous
            </button>
            <span>
              Page {data.page} of {data.totalPages}
            </span>
            <button
              disabled={data.page >= data.totalPages}
              onClick={() => goToPage(data.page + 1)}
            >
              Next
            </button>
          </nav>
        </>
      )}
      </div>
    </div>
  );
}

export default RecipeList;