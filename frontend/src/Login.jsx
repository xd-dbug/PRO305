import { useEffect, useState } from "react";
import { listRecipes } from "./api/client";
import "./Login.css"

function Login(){
    
    return(
<div  className="login-container">
        <h1>Please enter your email</h1>
        <textarea placeholder="Email" />
        <h1>Please enter your password</h1>
        <textarea placeholder="Password" />
        <button>Login</button>
    </div>

    )
    
}

export default Login;