import { useEffect, useState } from "react";
import { listRecipes } from "./api/client";
import { Routes, Route } from 'react-router-dom'
import Login from "./Login.jsx";
import Register from "./Register.jsx";
import Homepage from "./Homepage.jsx";
import Browser from "./Browser.jsx";
import RecipeList from "./RecipeList.jsx";
import Recipe from "./Recipe.jsx";


function App() {
 return(
  <Routes>
<Route path="/" element={<Homepage />} />
<Route path="/login" element={<Login />} />
<Route path="/register" element={<Register />} /> 
<Route path="/browser" element={<Browser />} />
<Route path="/recipe" element={<RecipeList />} />
<Route path="/recipes/:name" element={<Recipe />} />
  </Routes>
 );

}

export default App;
