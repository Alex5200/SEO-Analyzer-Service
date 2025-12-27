from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

def test_read():
    client = TestClient(app)  # ← если это падает — проблема в зависимостях
    response = client.get("/")
    assert response.status_code == 200