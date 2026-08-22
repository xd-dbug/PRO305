import { Routes, Route } from 'react-router-dom'
import Nav from "./Nav.jsx";
import Login from "./Login.jsx";
import Register from "./Register.jsx";
import Homepage from "./Homepage.jsx";
import Browser from "./Browser.jsx";
import RecipeList from "./RecipeList.jsx";
import Recipe from "./Recipe.jsx";
import RecipeCreate from "./RecipeCreate.jsx";
import MealPlan from "./MealPlan.jsx";


function App() {
 return(
  <>
    <Nav />
    <Routes>
      <Route path="/" element={<Homepage />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/browser" element={<Browser />} />
      <Route path="/recipes" element={<RecipeList />} />
      <Route path="/recipes/new" element={<RecipeCreate />} />
      <Route path="/recipes/:recipeId" element={<Recipe />} />
      <Route path="/mealplan" element={<MealPlan />} />
    </Routes>
  </>
 );

}

export default App;