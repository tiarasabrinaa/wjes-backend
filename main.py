import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import (
    clustering,
    ihk_forecast,
    bahan_pokok,
)
from loguru import logger

app = FastAPI(
    title='WJES',
    description='WJES services using FastAPI',
    version='0.1'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["DELETE", "GET", "POST", "PUT"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(ihk_forecast.router)
app.include_router(clustering.router)
app.include_router(bahan_pokok.router)

# Setup logging
logger.add(sys.stderr, level="TRACE")
logger.add(sys.stderr, format="{time} | {level} | {message}")
logger.add("/log/wjes.log", rotation="1 hour")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=1234, workers=1, reload=True)