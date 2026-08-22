import { Link, useLocation, useNavigate } from "react-router-dom";
import { getToken, setToken, setUserId } from "./api/client";
import "./Nav.css";

function Nav() {
  const navigate = useNavigate();
  useLocation(); // re-render on navigation so isAuthed picks up login/logout

  const isAuthed = Boolean(getToken());

  function handleLogout() {
    setToken(null);
    setUserId(null);
    navigate("/");
  }

  return (
    <nav className="site-nav">
      <Link to="/" className="site-nav-brand">
        🍲 RecipeShare
      </Link>
      <div className="site-nav-links">
        {isAuthed ? (
          <button type="button" className="site-nav-logout" onClick={handleLogout}>
            Log out
          </button>
        ) : (
          <>
            <Link to="/login">Log in</Link>
            <Link to="/register">Register</Link>
          </>
        )}
      </div>
    </nav>
  );
}

export default Nav;