import { Link } from "react-router-dom";
import "./NotFound.css";

function NotFound() {
  return (
    <div className="not-found-page">
      <p className="not-found-code">404</p>
      <h1>Page not found</h1>
      <p className="state-message">
        There's nothing here. <Link to="/">Go home</Link> or{" "}
        <Link to="/recipes">browse recipes</Link>.
      </p>
    </div>
  );
}

export default NotFound;