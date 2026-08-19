import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "./api/client";
import "./Register.css";

function Register() {
  const navigate = useNavigate();

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("idle"); // idle | submitting | error
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus("submitting");
    setError(null);
    try {
      await register(email, password, displayName);
      // Contract's POST /auth/register response has no token — register and
      // login are separate steps, so send them to log in next.
      navigate("/login?registered=1");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }

  const isSubmitting = status === "submitting";

  return (
    <div className="register-container">
      <h1>Create an account</h1>

      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Display name"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          required
          disabled={isSubmitting}
        />
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          disabled={isSubmitting}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          disabled={isSubmitting}
        />

        {status === "error" && <p className="register-error">{error}</p>}

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Creating account…" : "Create account"}
        </button>
      </form>

      <p className="register-alt">
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </div>
  );
}

export default Register;