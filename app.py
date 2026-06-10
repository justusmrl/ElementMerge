import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse

from infinitecraft import Element, InfiniteCraft
from infinitecraft.clients import CurlCffiClient
from infinitecraft.errors.clients import ClientResponseError


logger = logging.getLogger(__name__)


class ProxyCurlClient(CurlCffiClient):
    """
    Uses OUTBOUND_PROXY when configured.

    Example:
    OUTBOUND_PROXY=http://username:password@proxy-host:port
    """

    def __init__(self, base_url: str, *, headers: dict[str, str], **kwargs):
        session_options = {
            "timeout": 30,
        }

        proxy = os.getenv("OUTBOUND_PROXY")

        if proxy:
            session_options["proxy"] = proxy

        super().__init__(
            base_url,
            headers=headers,
            **session_options,
        )


game = InfiniteCraft(
    manual_control=True,
    debug=False,
    discoveries_storage="/tmp/discoveries.json",
    api_rate_limit=60,
    session_cls=ProxyCurlClient,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await game.start()

    try:
        yield
    finally:
        if not game.closed:
            await game.close()


app = FastAPI(lifespan=lifespan)


@app.get("/", response_class=PlainTextResponse)
async def root():
    return "Element Merge API is running"


@app.get("/pair", response_class=PlainTextResponse)
async def pair(
    first: str = Query(..., min_length=1, max_length=200),
    second: str = Query(..., min_length=1, max_length=200),
):
    first = first.strip()
    second = second.strip()

    try:
        result = await game.pair(
            Element(name=first),
            Element(name=second),
            store=False,
        )

    except ClientResponseError as exc:
        logger.exception("Neal.fun rejected the Infinite Craft request")

        return PlainTextResponse(
            "Infinite Craft upstream returned 403 Forbidden",
            status_code=502,
        )

    except Exception:
        logger.exception("Unexpected Infinite Craft request failure")

        return PlainTextResponse(
            "Infinite Craft upstream request failed",
            status_code=502,
        )

    if not result or not result.name:
        return "Nothing"

    emoji = result.emoji or ""
    return f"{emoji} {result.name}".strip()
