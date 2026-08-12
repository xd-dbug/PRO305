import { useEffect, useState } from "react";
import { listRecipes } from "./api/client";
import { Routes, Route } from 'react-router-dom'
import "./App.css";
import Login from "./Login.jsx";
import Register from "./Register.jsx";
import Homepage from "./Homepage.jsx";
import Browser from "./Browser.jsx";
import RecipeList from "./RecipeList.jsx";
import Recipe from "./Recipe.jsx";


function App() {
 
  <Routes>
<App path="/" element={<Homepage />} />
<App path="/login" element={<Login />} />
<App path="/register" element={<Register />} /> 
<App path="/browser" element={<Browser />} />
<App path="/recipe" element={<RecipeList />} />
<App path="/recipes/:name" element={<Recipe />} />
  </Routes>


}

export default App;
