import { useEffect, useState } from "react";
import { listRecipes } from "./api/client";
import "./Homepage.css"

function Homepage() {
  return (
    <div className="Homepage">
      <h1>Welcome</h1>
      <p>This is the homepage.</p>
    </div>
  );
}

export default Homepage;