import os
import re
import uuid

import openai
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_api_key, save_api_key
from app.rocco import RENDER_END, RENDER_START, SYSTEM_PROMPT, render_instruction
from app.targets import TARGETS

app = FastAPI(title="Rocco V")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("ROCCOV_SECRET_KEY", "dev-secret-change-me"),
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Single-user local tool: conversation history (and the last render) live
# in memory, keyed by a session cookie. No need for a database.
CONVERSATIONS: dict[str, list[dict]] = {}
LAST_RENDER: dict[str, dict] = {}

RENDER_PATTERN = re.compile(
    re.escape(RENDER_START) + r"(.*?)" + re.escape(RENDER_END), re.S
)

# Change here if a different OpenAI model is wanted.
CHAT_MODEL = "gpt-5.6-luna"


def get_session_id(request: Request) -> str:
    session_id = request.session.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        request.session["session_id"] = session_id
    return session_id


def extract_render(text: str):
    match = RENDER_PATTERN.search(text)
    if not match:
        return text.strip(), None
    rendered = match.group(1).strip()
    chat_text = (text[: match.start()] + text[match.end() :]).strip()
    return chat_text, rendered


def friendly_api_error(exc: openai.OpenAIError) -> str:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        message = body.get("error", {}).get("message")
        if message:
            return message
    return str(exc)


def run_chat_turn(session_id: str, message: str) -> dict:
    history = CONVERSATIONS.setdefault(session_id, [])
    history.append({"role": "user", "content": message})

    try:
        client = openai.OpenAI(api_key=get_api_key())
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            max_completion_tokens=4096,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
        )
    except openai.OpenAIError as exc:
        # Roll back the unanswered turn so history stays alternating
        # user/assistant for the next attempt.
        history.pop()
        return {
            "user_message": message,
            "assistant_message": None,
            "rendered": None,
            "error": friendly_api_error(exc),
        }

    reply_text = response.choices[0].message.content or ""
    if not reply_text.strip() and response.choices[0].finish_reason == "length":
        history.pop()
        return {
            "user_message": message,
            "assistant_message": None,
            "rendered": None,
            "error": (
                "The model used its whole token budget on internal reasoning "
                "and had none left to write a visible reply. Try a shorter "
                "message, or raise max_completion_tokens in app/main.py."
            ),
        }

    chat_text, rendered = extract_render(reply_text)
    history.append({"role": "assistant", "content": chat_text})

    return {"user_message": message, "assistant_message": chat_text, "rendered": rendered}


@app.get("/setup", response_class=HTMLResponse)
def setup_form(request: Request):
    return templates.TemplateResponse(request, "setup.html", {"error": None})


@app.post("/setup", response_class=HTMLResponse)
def setup_submit(request: Request, api_key: str = Form(...)):
    api_key = api_key.strip()
    if not api_key:
        return templates.TemplateResponse(
            request, "setup.html", {"error": "API key is required."}
        )
    save_api_key(api_key)
    return RedirectResponse(url="/", status_code=303)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    if not get_api_key():
        return RedirectResponse(url="/setup", status_code=303)
    session_id = get_session_id(request)
    history = CONVERSATIONS.setdefault(session_id, [])
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "history": history,
            "targets": TARGETS,
            "last_render": LAST_RENDER.get(session_id),
        },
    )


@app.post("/chat")
def chat(request: Request, message: str = Form(...)):
    if not get_api_key():
        return JSONResponse({"error": "not_authorized"}, status_code=401)
    session_id = get_session_id(request)
    result = run_chat_turn(session_id, message)
    result["target_label"] = None
    if result.get("rendered"):
        LAST_RENDER[session_id] = {"text": result["rendered"], "target_label": None}
    return JSONResponse(result)


@app.post("/render/{target_key}")
def trigger_render(request: Request, target_key: str):
    if not get_api_key():
        return JSONResponse({"error": "not_authorized"}, status_code=401)
    target = TARGETS.get(target_key)
    if not target:
        return JSONResponse({"error": "unknown_target"}, status_code=404)
    session_id = get_session_id(request)
    instruction = render_instruction(target["label"], target["style"])
    result = run_chat_turn(session_id, instruction)
    result["target_label"] = target["label"] if result.get("rendered") else None
    if result.get("rendered"):
        LAST_RENDER[session_id] = {
            "text": result["rendered"],
            "target_label": result["target_label"],
        }
    return JSONResponse(result)
