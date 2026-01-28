import os
from contextlib import asynccontextmanager

import bugsnag
from dotenv import load_dotenv
from fastapi import FastAPI, Body

from llm_reply import LlmReplyService

load_dotenv()

llm_service: None | LlmReplyService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm_service
    llm_service = LlmReplyService()  # loads model once per process
    yield
    print("Shutting down: cleanup if needed")


app = FastAPI(lifespan=lifespan)

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
        result = llm_service.get_local_reply(data)
        return {'message': result}
    except Exception as e:
        bugsnag.notify(e)
