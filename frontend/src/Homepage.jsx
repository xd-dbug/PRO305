import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listRecipes } from "./api/client.js";
import "./Homepage.css";

function Homepage() {
  const [recentRecipes, setRecentRecipes] = useState([]);
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    listRecipes({ page: 1, limit: 4 })
      .then((res) => {
        if (cancelled) return;
        setRecentRecipes(res.recipes);
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
  }, []);

  return (
    <div className="Homepage">
      <div className="homepage-content">
        <section className="intro-box">
          <h1>Welcome</h1>
          <p>
            Browse recipes from the community, save your own favorites, and let us
            put together a meal plan for the week — all in one place.
          </p>
        </section>

        <section className="dashboard">
          <div className="dashboard-tiles">
            <Link to="/recipes" className="dashboard-tile">
              <span className="tile-icon" aria-hidden="true">📖</span>
              <h2>Browse recipes</h2>
              <p>See everything in the collection.</p>
            </Link>
            <Link to="/browser" className="dashboard-tile">
              <span className="tile-icon" aria-hidden="true">🔎</span>
              <h2>Discover</h2>
              <p>Find something new from other cooks.</p>
            </Link>
            <Link to="/recipes/new" className="dashboard-tile">
              <span className="tile-icon" aria-hidden="true">➕</span>
              <h2>Add a recipe</h2>
              <p>Save one of your own.</p>
            </Link>
            <Link to="/mealplan" className="dashboard-tile">
              <span className="tile-icon" aria-hidden="true">🗓️</span>
              <h2>Plan meals</h2>
              <p>Generate a plan for the week.</p>
            </Link>
          </div>

          <div className="dashboard-recent">
            <h2>Recently added</h2>

            {status === "loading" && <p className="state-message">Loading recipes…</p>}

            {status === "error" && (
              <p className="state-message error">Couldn't load recipes: {error}</p>
            )}

            {status === "ready" && recentRecipes.length === 0 && (
              <p className="state-message">
                No recipes yet — <Link to="/recipes/new">add the first one</Link>.
              </p>
            )}

            {status === "ready" && recentRecipes.length > 0 && (
              <ul className="recent-grid">
                {recentRecipes.map((recipe) => (
                  <li key={recipe.recipeId}>
                    <Link to={`/recipes/${recipe.recipeId}`} className="recent-card">
                      <div className="recent-photo">
                        {recipe.photoUrl ? (
                          <img src={recipe.photoUrl} alt={recipe.title} />
                        ) : (
                          <div className="recent-photo-placeholder" aria-hidden="true">
                            🍽️
                          </div>
                        )}
                      </div>
                      <span className="recent-title">{recipe.title}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

export default Homepage;