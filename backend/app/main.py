from fastapi import FastAPI

app = FastAPI(title="Scentfolio")

@app.get("/api/health")
def health():
    return {"status": "ok"}
