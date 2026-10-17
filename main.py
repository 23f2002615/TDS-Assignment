import time
import uuid
from fastapi import FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGIN = "https://dash-55m035.example.com"
EMAIL = "23f2002615@ds.study.iitm.ac.in"

app = FastAPI()

# Strict CORS: only this exact origin is allowed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_required_headers(request: Request, call_next):
    start = time.perf_counter()

    response = await call_next(request)

    elapsed = time.perf_counter() - start
    response.headers["X-Request-ID"] = str(uuid.uuid4())
    response.headers["X-Process-Time"] = f"{max(elapsed, 0):.6f}"
    return response

@app.get("/stats")
def stats(values: str = Query(...)):
    try:
        nums = [int(x.strip()) for x in values.split(",") if x.strip() != ""]
    except ValueError:
        return Response(
            content='{"error": "values must be comma-separated integers"}',
            status_code=400,
            media_type="application/json",
        )

    count = len(nums)
    total = sum(nums)

    return {
        "email": EMAIL,
        "count": count,
        "sum": total,
        "min": min(nums),
        "max": max(nums),
        "mean": total / count,
    }
