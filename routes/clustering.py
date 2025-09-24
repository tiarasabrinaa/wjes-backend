from fastapi import APIRouter, Depends, HTTPException
from dependencies import get_api_key
from utils import json_parse
from pathlib import Path
import base64
from loguru import logger
from llm_engine import telkomllm_call_ocr, telkommultimodal_call

router = APIRouter(tags=["Clustering"])

@router.get("/wjes/clustering_twitter")
async def clustering_twitter(x_api_key: str = Depends(get_api_key)):
    temp_dir = Path("temp_uploads")
    base = "Laporan Pekerjaan Selesai 100"
    txt = next(temp_dir.glob(f"{base}*.txt"), None)
    img = next(temp_dir.glob(f"{base}*.jpg"), None)
    if not txt: raise HTTPException(404, "Text not found")
    if not img: raise HTTPException(404, "Image not found")

    with open(txt, "r", encoding="utf-8") as f:
        text = f.read()

    info = await telkomllm_call_ocr(waspang_extraction_prompt, text)
    parsed_info = json_parse(info)

    with open(img, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    # sign = await telkommultimodal_call(sign_check_prompt_multimodal, b64)
    # parsed_sign = json_parse(sign)

    return {
        "status": "success",
        "laporan_info": parsed_info,
        "signature_verification": parsed_sign
    }