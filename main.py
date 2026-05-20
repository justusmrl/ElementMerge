import os
from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse
from infinitecraft import InfiniteCraft, Element

app = FastAPI()

game = InfiniteCraft(
    manual_control=True,
    debug=False,
    discoveries_storage="/tmp/discoveries.json",
)


@app.on_event("startup")
async def startup():
    await game.start()


@app.on_event("shutdown")
async def shutdown():
    await game.close()


@app.get("/pair", response_class=PlainTextResponse)
async def pair(
    first: str = Query(...),
    second: str = Query(...),
):
    result = await game.pair(
        Element(name=first),
        Element(name=second),
        store=False,
    )

    if not result:
        return "Nothing"

    return f"{result.emoji} {result.name}"
    
