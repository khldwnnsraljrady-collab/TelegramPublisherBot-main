import os
import uvicorn


if __name__ == "__main__":
    port = int(os.getenv("SERVER_PORT", "8000"))

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port
    )
