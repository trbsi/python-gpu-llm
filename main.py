from typing import Union

from fastapi import FastAPI, Body

app = FastAPI()

@app.get("/health")
def health():
    return {"success": "ok"}

@app.post("/reply")
def reply(data: list = Body(...)):
    service = LlmReplyService()
    result = service.get_local_reply(data)
    return {'message': result}
