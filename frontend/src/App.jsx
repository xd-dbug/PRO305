import { Routes, Route } from 'react-router-dom'
import ErrorBoundary from "./ErrorBoundary.jsx";
import Nav from "./Nav.jsx";
import Login from "./Login.jsx";
import Register from "./Register.jsx";
import Homepage from "./Homepage.jsx";
import Browser from "./Browser.jsx";
import RecipeList from "./RecipeList.jsx";
import Recipe from "./Recipe.jsx";
import RecipeCreate from "./RecipeCreate.jsx";
import MealPlan from "./MealPlan.jsx";
import NotFound from "./NotFound.jsx";


function App() {
 return(
  <>
    <Nav />
    <ErrorBoundary>
      <Routes>
        <Route path="/" element={<Homepage />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/browser" element={<Browser />} />
        <Route path="/recipes" element={<RecipeList />} />
        <Route path="/recipes/new" element={<RecipeCreate />} />
        <Route path="/recipes/:recipeId" element={<Recipe />} />
        <Route path="/recipes/:recipeId/edit" element={<RecipeCreate />} />
        <Route path="/mealplan" element={<MealPlan />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </ErrorBoundary>
  </>
 );

}

export default App;