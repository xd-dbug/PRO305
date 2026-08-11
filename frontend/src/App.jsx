import { useEffect, useState } from "react";
import { listRecipes } from "./api/client";
import "./App.css";

function App() {
  const [recipes, setRecipes] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    listRecipes()
      .then((data) => setRecipes(data.recipes))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="App">
      <h1>Recipe Sharing</h1>
      {error && <p role="alert">Could not load recipes: {error}</p>}
      <ul>
        {recipes.map((recipe) => (
          <li key={recipe.id}>{recipe.title}</li>
        ))}
      </ul>
    </div>
  );
}

export default App;
