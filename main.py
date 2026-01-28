import os

import bugsnag
from dotenv import load_dotenv
from fastapi import FastAPI, Body

from llm_reply import LlmReplyService

app = FastAPI()
load_dotenv()
bugsnag_api_key = os.getenv("BUGSNAG_API_KEY")
bugsnag.configure(
    api_key=os.getenv("BUGSNAG_API_KEY"),
    project_root=os.path.dirname(os.path.abspath(__file__)),
)


@app.get("/health")
def health():
    return {"success": "ok"}


@app.get("/bugsnag")
def health():
    bugsnag.notify(Exception('Test exception from GPU'))
    return {"message": "bugsnag sent"}


@app.post("/reply")
def reply(data: list = Body(...)):
    try:
        service = LlmReplyService()
        result = service.get_local_reply(data)
        return {'message': result}
    except Exception as e:
        bugsnag.notify(e)
