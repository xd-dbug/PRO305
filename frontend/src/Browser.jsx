import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { listRecipes, getUserId } from "./api/client";
import "./Browser.css";

function Browser() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Number(searchParams.get("page")) || 1;
  const tag = searchParams.get("tag") || "";

  const [data, setData] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const [error, setError] = useState(null);
  const [tagInput, setTagInput] = useState(tag);

  const currentUserId = getUserId();

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

  // API_CONTRACT.md has no "exclude my recipes" / authorId query param on
  // GET /recipes, so this filters client-side once we know who's logged in.
  // Until there's a real auth flow storing a userId, currentUserId is null
  // and everyone's recipes show up — that's expected, not a bug. Filtering
  // per-page like this can also make a page look thinner than its limit when
  // a chunk of it turns out to be yours; worth flagging to Person A as a
  // contract addition (e.g. ?excludeAuthor=me) if this needs to be exact.
  const otherPeoplesRecipes = data
    ? data.recipes.filter((recipe) => !currentUserId || recipe.authorId !== currentUserId)
    : [];

  return (
    <div className="browser-page">
      <header className="browser-header">
        <h1>Browse recipes</h1>
        <p className="browser-intro">Discover what other people are cooking.</p>
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

      {status === "ready" && otherPeoplesRecipes.length === 0 && (
        <p className="state-message">
          No other recipes {tag ? `tagged "${tag}"` : "to browse"} right now.
        </p>
      )}

      {status === "ready" && otherPeoplesRecipes.length > 0 && (
        <>
          <ul className="browser-grid">
            {otherPeoplesRecipes.map((recipe) => (
              <li className="browser-card" key={recipe.recipeId}>
                <Link to={`/recipes/${recipe.recipeId}`}>
                  <div className="browser-photo">
                    {recipe.photoUrl ? (
                      <img src={recipe.photoUrl} alt={recipe.title} />
                    ) : (
                      <div className="browser-photo-placeholder" aria-hidden="true">
                        🍽️
                      </div>
                    )}
                  </div>
                  <h2>{recipe.title}</h2>
                  <span className="browser-rating">
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
  );
}

export default Browser;