import hashlib
import os

from mcp.server.mcpserver import MCPServer, Context

EMAIL = "23f2002615@ds.study.iitm.ac.in"

mcp = MCPServer("exam-mcp-server")


@mcp.tool(
    name="solve_challenge",
    description="Returns the first 16 lowercase hex characters of SHA-256(challenge:email)."
)
def solve_challenge(ctx: Context) -> str:
    headers = ctx.request_context.request.headers

    challenge = headers.get("x-exam-challenge")

    if not challenge:
        raise ValueError("Missing X-Exam-Challenge header")

    text = f"{challenge}:{EMAIL}"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()

    return digest[:16]


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
        json_response=True,
        stateless_http=True,
    )