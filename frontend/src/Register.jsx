import "./Register.css";

function Register() {
  return (
    <div className="register-container">
        <h1>Please enter your username</h1>  
         <textarea placeholder="UserName" />
       <h1>Please enter your email</h1>
        <textarea placeholder="Email" />
        <h1>Please enter your password</h1>
        <textarea placeholder="Password" />
        <button>Register</button>
    </div>
  );
}

export default Register;