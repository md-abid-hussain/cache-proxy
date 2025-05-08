import logging

import httpx
import typer
import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from typing_extensions import Annotated

PORT = None
ORIGIN = None

app = FastAPI()

cache = {}

logging.addLevelName(21, "X-CACHE")
logging.addLevelName(22, "SERVER-INFO")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

logger = logging.getLogger(__name__)


@app.get("/favicon.ico")
async def block_favicon():
    logger.log(22, "Blocked /favicon.ico")
    raise HTTPException(status_code=404, detail="Favicon not served.")


@app.get("/{path:path}")
async def forward(path: str):
    path = path[0:-1] if path.endswith("/") else path
    logger.log(22, f"GET {ORIGIN}/{path}")

    if path in cache:
        logger.log(21, "HIT")
        return JSONResponse(cache[path], status_code=status.HTTP_200_OK)

    response = httpx.get(f"{ORIGIN}/{path}")

    if response.status_code == 200:
        logger.log(21, "MISS")
        cache.setdefault(path, response.json())
        return response.json()

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


def cache_proxy(
    port: Annotated[
        int, typer.Option(help="PORT on which you want to run server")
    ] = None,
    origin: Annotated[
        str, typer.Option(help="ORIGIN of server which resource you want to cache")
    ] = None,
    clear_cache: Annotated[bool, typer.Option(help="Clear cache")] = False,
):
    if clear_cache:
        logger.log(22, "Cache is cleared")
        return

    if port is None or origin is None:
        typer.secho(
            "Error: --port and --origin are required when --clear-cache is not set.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    global PORT, ORIGIN
    PORT = port
    ORIGIN = origin[0:-1] if origin.endswith("/") else origin

    logger.log(22, f"Cache Proxy Server Starting at {PORT} for {ORIGIN}")
    uvicorn.run(app, host="localhost", port=PORT, log_config=None)


def main() -> None:
    typer.run(cache_proxy)
