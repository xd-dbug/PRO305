import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getToken, listSavedRecipes } from "./api/client";
import "./RecipeList.css";

function SavedRecipes() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Number(searchParams.get("page")) || 1;

  const [data, setData] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const [error, setError] = useState(null);

  const isAuthed = Boolean(getToken());

  useEffect(() => {
    if (!isAuthed) return;
    let cancelled = false;
    setStatus("loading");
    listSavedRecipes({ page })
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
  }, [page, isAuthed]);

  function goToPage(nextPage) {
    setSearchParams({ page: String(nextPage) });
  }

  return (
    <div className="recipe-list-page">
      <div className="recipe-list-content">
        <header className="recipe-list-header">
          <h1>Saved recipes</h1>
        </header>

        {!isAuthed && (
          <p className="state-message">
            <Link to="/login">Log in</Link> to see your saved recipes.
          </p>
        )}

        {isAuthed && status === "loading" && <p className="state-message">Loading saved recipes…</p>}

        {isAuthed && status === "error" && (
          <p className="state-message error">Couldn't load saved recipes: {error}</p>
        )}

        {isAuthed && status === "ready" && data.recipes.length === 0 && (
          <p className="state-message">
            You haven't saved any recipes yet. <Link to="/recipes">Browse recipes</Link> to find some.
          </p>
        )}

        {isAuthed && status === "ready" && data.recipes.length > 0 && (
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

            <nav className="pagination" aria-label="Saved recipe pages">
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

export default SavedRecipes;
