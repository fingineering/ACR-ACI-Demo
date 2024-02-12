from fastapi import FastAPI

# A very minimalistic FastAPI application

app FastAPI()


@app.get("/")
def index():
    return {"Hello": "World"}


@app.get("/health")
def health():
    return "OK"
