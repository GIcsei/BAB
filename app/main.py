# FastAPI (backend)
from fastapi import FastAPI, HTTPException, Request, Depends
from firebase_admin import auth, initialize_app, credentials

cred = credentials.Certificate("./ersterepgen-ebd117266a99.json")
initialize_app(cred)
app = FastAPI()

@app.post("/auth/login")
def login(payload: dict):
    email = payload.get("email")
    password = payload.get("password")
    try:
        # Use Firebase REST API to sign in (not admin SDK)
        import requests
        r = requests.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=YOUR_API_KEY",
            json={"email": email, "password": password, "returnSecureToken": True}
        )
        if r.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid login.")
        return r.json()  # contains idToken, refreshToken, etc.
    except Exception:
        raise HTTPException(status_code=500, detail="Login failed.")

@app.get("/hello")
def hello_world():
    print('I\'m working!!!')
    return {"message": "Hello World"}

if __name__ == "__main__":
    hello_world()