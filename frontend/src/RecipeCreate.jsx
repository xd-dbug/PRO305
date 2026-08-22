import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { createRecipe, getRecipe, getToken, getUserId, updateRecipe } from "./api/client";
import "./RecipeCreate.css";

const emptyIngredient = () => ({ name: "", amount: "" });

function RecipeCreate() {
  const navigate = useNavigate();
  const { recipeId } = useParams();
  const isEditMode = Boolean(recipeId);
  const isAuthed = Boolean(getToken());

  const [title, setTitle] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const [servings, setServings] = useState("");
  const [prepTime, setPrepTime] = useState("");
  const [cookTime, setCookTime] = useState("");
  const [notes, setNotes] = useState("");
  const [ingredients, setIngredients] = useState([emptyIngredient()]);
  const [steps, setSteps] = useState([""]);
  const [status, setStatus] = useState(isEditMode ? "loading" : "idle"); // loading | idle | saving | error
  const [error, setError] = useState(null);
  const [forbidden, setForbidden] = useState(false);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    if (!isEditMode) return;
    let cancelled = false;
    getRecipe(recipeId)
      .then((recipe) => {
        if (cancelled) return;
        if (recipe.authorId !== getUserId()) {
          setForbidden(true);
          setStatus("idle");
          return;
        }
        setTitle(recipe.title || "");
        setTagsInput((recipe.tags || []).join(", "));
        setServings(recipe.servings || "");
        setPrepTime(recipe.prepTime || "");
        setCookTime(recipe.cookTime || "");
        setNotes(recipe.notes || "");
        setIngredients(recipe.ingredients?.length ? recipe.ingredients : [emptyIngredient()]);
        setSteps(recipe.steps?.length ? recipe.steps : [""]);
        setStatus("idle");
      })
      .catch((err) => {
        if (cancelled) return;
        setLoadError(err.message);
        setStatus("idle");
      });
    return () => {
      cancelled = true;
    };
  }, [isEditMode, recipeId]);

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

    // Shape matches the contract: same body as GET /recipes/{id} minus recipeId/avgRating.
    // servings/prepTime/cookTime/notes are NOT in API_CONTRACT.md yet — sending
    // them is harmless (most APIs ignore unknown fields) but they won't persist
    // until Person A adds them to the recipe schema and it's re-signed-off.
    const payload = {
      title: title.trim(),
      servings: servings.trim() || undefined,
      prepTime: prepTime.trim() || undefined,
      cookTime: cookTime.trim() || undefined,
      notes: notes.trim() || undefined,
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
      if (isEditMode) {
        await updateRecipe(recipeId, payload);
        navigate(`/recipes/${recipeId}`);
      } else {
        const created = await createRecipe(payload);
        navigate(`/recipes/${created.recipeId}`);
      }
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }

  if (!isAuthed) {
    return (
      <div className="recipe-create-page">
        <div className="recipe-create-content">
          <p className="state-message">
            You need to be logged in to create a recipe. <Link to="/login">Log in</Link>
          </p>
        </div>
      </div>
    );
  }

  if (status === "loading") {
    return (
      <div className="recipe-create-page">
        <div className="recipe-create-content">
          <p className="state-message">Loading recipe…</p>
        </div>
      </div>
    );
  }

  if (forbidden) {
    return (
      <div className="recipe-create-page">
        <div className="recipe-create-content">
          <p className="state-message error">You can only edit your own recipes.</p>
          <Link to={`/recipes/${recipeId}`}>← Back to recipe</Link>
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="recipe-create-page">
        <div className="recipe-create-content">
          <p className="state-message error">Couldn't load this recipe: {loadError}</p>
          <Link to="/recipes">← All recipes</Link>
        </div>
      </div>
    );
  }

  const isSaving = status === "saving";

  return (
    <div className="recipe-create-page">
      <div className="recipe-create-content">
        <form onSubmit={handleSubmit}>
          <header className="recipe-title-bar">
            <input
              className="title-input"
              type="text"
              placeholder="Recipe title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              disabled={isSaving}
            />
            <input
              className="tags-input"
              type="text"
              placeholder="Tags, comma separated"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
              disabled={isSaving}
            />
          </header>

          <div className="recipe-meta-row">
            <div className="meta-item">
              <span className="meta-label">Servings</span>
              <input
                className="meta-input"
                type="text"
                value={servings}
                onChange={(e) => setServings(e.target.value)}
                disabled={isSaving}
              />
            </div>
            <div className="meta-item">
              <span className="meta-label">Prep time</span>
              <input
                className="meta-input"
                type="text"
                placeholder="15 min"
                value={prepTime}
                onChange={(e) => setPrepTime(e.target.value)}
                disabled={isSaving}
              />
            </div>
            <div className="meta-item">
              <span className="meta-label">Cook time</span>
              <input
                className="meta-input"
                type="text"
                placeholder="30 min"
                value={cookTime}
                onChange={(e) => setCookTime(e.target.value)}
                disabled={isSaving}
              />
            </div>
          </div>

          <div className="recipe-layout">
            <div className="recipe-layout-left">
              <fieldset className="recipe-box ingredients-box">
                <legend>Ingredients</legend>
                {ingredients.map((ing, i) => (
                  <div className="ingredient-row" key={i}>
                    <input
                      type="text"
                      placeholder="Amount"
                      value={ing.amount}
                      onChange={(e) => updateIngredient(i, "amount", e.target.value)}
                      disabled={isSaving}
                    />
                    <input
                      type="text"
                      placeholder="Ingredient"
                      value={ing.name}
                      onChange={(e) => updateIngredient(i, "name", e.target.value)}
                      disabled={isSaving}
                    />
                    {ingredients.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeIngredient(i)}
                        aria-label="Remove ingredient"
                        disabled={isSaving}
                      >
                        ✕
                      </button>
                    )}
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => setIngredients((prev) => [...prev, emptyIngredient()])}
                  disabled={isSaving}
                >
                  + Add ingredient
                </button>
              </fieldset>

              <fieldset className="recipe-box notes-box">
                <legend>Notes</legend>
                <textarea
                  placeholder="Anything worth remembering — substitutions, timing tricks, etc."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  disabled={isSaving}
                />
              </fieldset>
            </div>

            <div className="recipe-layout-right">
              <fieldset className="recipe-box directions-box">
                <legend>Directions</legend>
                {steps.map((step, i) => (
                  <div className="step-row" key={i}>
                    <span className="step-number">{i + 1}</span>
                    <textarea value={step} onChange={(e) => updateStep(i, e.target.value)} disabled={isSaving} />
                    {steps.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeStep(i)}
                        aria-label="Remove step"
                        disabled={isSaving}
                      >
                        ✕
                      </button>
                    )}
                  </div>
                ))}
                <button type="button" onClick={() => setSteps((prev) => [...prev, ""])} disabled={isSaving}>
                  + Add step
                </button>
              </fieldset>

              <div className="recipe-box photo-box">
                <p className="photo-box-note">
                  Photos upload after saving — add one from the recipe page once it's created.
                </p>
              </div>
            </div>
          </div>

          {status === "error" && <p className="state-message error">{error}</p>}

          <button type="submit" className="submit-btn" disabled={isSaving}>
            {isSaving ? "Saving…" : isEditMode ? "Save changes" : "Save recipe"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default RecipeCreate;