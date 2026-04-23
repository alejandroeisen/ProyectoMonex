from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, sheets, internal
from app.database import init_db

app = FastAPI(title="Intelimed Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(sheets.router, prefix="/sheets", tags=["sheets"])
app.include_router(internal.router)   # no prefix — endpoint is /internal/push


@app.get("/health")
def health():
    return {"status": "ok"}
