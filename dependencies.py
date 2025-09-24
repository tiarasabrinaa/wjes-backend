# dependencies.py
import os
from fastapi import Security, HTTPException
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
from dotenv import load_dotenv

load_dotenv('.env', override=True)
API_KEY_HEADER = APIKeyHeader(name="x-api-key", auto_error=True)
ACCESS_KEY = os.getenv('X_API_KEY')

async def get_api_key(api_key_header: str = Security(API_KEY_HEADER)):
    if api_key_header == ACCESS_KEY:
        return api_key_header
    else:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Could not validate API KEY"
        )