import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ----- Your assigned values -----
TOTAL_ORDERS = 57
RATE_LIMIT = 19          # requests
RATE_WINDOW = 10         # seconds

app = FastAPI(title="Orders API")

# ----- CORS: allow the grader page/browser -----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- 1. Idempotent order creation -----

class OrderCreate(BaseModel):
    item: str = "default item"
    quantity: int = 1

# key -> order response
idempotency_store = {}

@app.post("/orders", status_code=201)
def create_order(
    order: OrderCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")

    # If this exact key was used before, return the same saved order.
    if idempotency_key in idempotency_store:
        return idempotency_store[idempotency_key]

    new_order = {
        "id": str(uuid.uuid4()),
        "item": order.item,
        "quantity": order.quantity,
        "created_at": int(time.time()),
    }

    idempotency_store[idempotency_key] = new_order
    return new_order


# ----- 2. Cursor pagination -----

@app.get("/orders")
def list_orders(
    limit: int = Query(default=10, ge=1, le=100),
    cursor: str | None = Query(default=None),
):
    # Cursor means: "start after this order ID".
    start_after = 0

    if cursor:
        try:
            start_after = int(cursor)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor")

    # IDs are 1..57. Start at cursor + 1.
    start_id = start_after + 1
    end_id = min(start_id + limit - 1, TOTAL_ORDERS)

    items = [
        {"id": order_id, "item": f"Order {order_id}", "quantity": 1}
        for order_id in range(start_id, end_id + 1)
    ]

    next_cursor = None
    if end_id < TOTAL_ORDERS:
        next_cursor = str(end_id)

    return {
        "items": items,
        "next_cursor": next_cursor,
    }


# ----- 3. Per-client rate limiting -----

# client_id -> timestamps of recent requests
request_history = defaultdict(deque)

@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    client_id = request.headers.get("X-Client-Id")

    # Only rate-limit requests that identify a client.
    if client_id:
        now = time.time()
        history = request_history[client_id]

        # Remove requests older than the 10-second window.
        while history and now - history[0] >= RATE_WINDOW:
            history.popleft()

        if len(history) >= RATE_LIMIT:
            # Wait until the oldest request leaves the window.
            retry_after = max(1, int(RATE_WINDOW - (now - history[0])) + 1)
            return Response(
                content='{"detail":"Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(retry_after)},
            )

        history.append(now)

    return await call_next(request)


@app.get("/")
def root():
    return {
        "service": "orders-api",
        "total_orders": TOTAL_ORDERS,
        "rate_limit": f"{RATE_LIMIT} requests per {RATE_WINDOW} seconds per client",
    }