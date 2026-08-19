import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createRecipe, getToken } from "./api/client";
import "./RecipeCreate.css";

const emptyIngredient = () => ({ name: "", amount: "" });

function RecipeCreate() {
  const navigate = useNavigate();
  // const isAuthed = Boolean(getToken());

  const [title, setTitle] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const [ingredients, setIngredients] = useState([emptyIngredient()]);
  const [steps, setSteps] = useState([""]);
  const [status, setStatus] = useState("idle"); // idle | saving | error
  const [error, setError] = useState(null);

  function updateIngredient(index, field, value) {
    setIngredients((prev) => prev.map((ing, i) => (i === index ? { ...ing, [field]: value } : ing)));
  }

  function removeIngredient(index) {
    setIngredients((prev) => prev.filter((_, i) => i !== index));
  }

  function updateStep(index, value) {
    setSteps((prev) => prev.map((s, i) => (i === index ? value : s)));
  }

  function removeStep(index) {
    setSteps((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus("saving");
    setError(null);

    // Shape matches the contract: same body as GET /recipes/{id} minus recipeId/avgRating
    const payload = {
      title: title.trim(),
      ingredients: ingredients
        .filter((ing) => ing.name.trim())
        .map((ing) => ({ name: ing.name.trim(), amount: ing.amount.trim() })),
      steps: steps.map((s) => s.trim()).filter(Boolean),
      photoUrl: null,
      tags: tagsInput
        .split(",")
        .map((t) => t.trim().toLowerCase())
        .filter(Boolean),
    };

    try {
      const created = await createRecipe(payload);
      navigate(`/recipes/${created.recipeId}`);
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }

  // if (!isAuthed) {
  //   return (
  //     <div className="recipe-create-page">
  //       <p className="state-message">
  //         You need to be logged in to create a recipe. <Link to="/login">Log in</Link>
  //       </p>
  //     </div>
  //   );
  // }

  return (
    <div className="recipe-create-page">
      <div className="recipe-create-content">
      <h1>New recipe</h1>
      <form onSubmit={handleSubmit}>
        <label>
          Title
          <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} required />
        </label>

        <label>
          Tags <span className="hint">(comma separated)</span>
          <input
            type="text"
            value={tagsInput}
            onChange={(e) => setTagsInput(e.target.value)}
            placeholder="vegetarian, gluten-free"
          />
        </label>

        <fieldset>
          <legend>Ingredients</legend>
          {ingredients.map((ing, i) => (
            <div className="ingredient-row" key={i}>
              <input
                type="text"
                placeholder="Amount"
                value={ing.amount}
                onChange={(e) => updateIngredient(i, "amount", e.target.value)}
              />
              <input
                type="text"
                placeholder="Ingredient"
                value={ing.name}
                onChange={(e) => updateIngredient(i, "name", e.target.value)}
              />
              {ingredients.length > 1 && (
                <button type="button" onClick={() => removeIngredient(i)} aria-label="Remove ingredient">
                  ✕
                </button>
              )}
            </div>
          ))}
          <button type="button" onClick={() => setIngredients((prev) => [...prev, emptyIngredient()])}>
            + Add ingredient
          </button>
        </fieldset>

        <fieldset>
          <legend>Steps</legend>
          {steps.map((step, i) => (
            <div className="step-row" key={i}>
              <span className="step-number">{i + 1}</span>
              <textarea value={step} onChange={(e) => updateStep(i, e.target.value)} />
              {steps.length > 1 && (
                <button type="button" onClick={() => removeStep(i)} aria-label="Remove step">
                  ✕
                </button>
              )}
            </div>
          ))}
          <button type="button" onClick={() => setSteps((prev) => [...prev, ""])}>
            + Add step
          </button>
        </fieldset>

        {status === "error" && <p className="state-message error">{error}</p>}

        <button type="submit" className="submit-btn" disabled={status === "saving"}>
          {status === "saving" ? "Saving…" : "Save recipe"}
        </button>
      </form>
      </div>
    </div>
  );
}

export default RecipeCreate;