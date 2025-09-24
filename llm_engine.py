import os
import json
import httpx
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv('.env')

URL_CUSTOM_LLM = os.getenv('URL_CUSTOM_LLM_APILOGY')
TOKEN_CUSTOM_LLM = os.getenv('TOKEN_CUSTOM_LLM_APILOGY')

URL_CUSTOM_LMM = os.getenv('URL_CUSTOM_LMM')
TOKEN_CUSTOM_LMM = os.getenv('TOKEN_CUSTOM_LMM')

URL_CUSTOM_NANONETS = os.getenv('URL_CUSTOM_NANONETS')
TOKEN_CUSTOM_NANONETS = os.getenv('TOKEN_CUSTOM_NANONETS')

# Debug: Print loaded environment variables (masked)
logger.debug(f"URL_CUSTOM_LLM loaded: {'Yes' if URL_CUSTOM_LLM else 'No'}")
logger.debug(f"TOKEN_CUSTOM_LLM loaded: {'Yes' if TOKEN_CUSTOM_LLM else 'No'}")
logger.debug(f"URL_CUSTOM_LMM loaded: {'Yes' if URL_CUSTOM_LMM else 'No'}")
logger.debug(f"TOKEN_CUSTOM_LMM loaded: {'Yes' if TOKEN_CUSTOM_LMM else 'No'}")
logger.debug(f"URL_CUSTOM_NANONETS loaded: {'Yes' if URL_CUSTOM_NANONETS else 'No'}")
logger.debug(f"TOKEN_CUSTOM_NANONETS loaded: {'Yes' if TOKEN_CUSTOM_NANONETS else 'No'}")

async def telkomllm_call_ocr(extraction_prompt, ocr_result, reasoning=False):
    """
    Makes an asynchronous API call to the Telkom LLM API.
    """
    try:
        # Validate environment variables
        if not URL_CUSTOM_LLM:
            error_msg = "URL_CUSTOM_LLM_APILOGY not found in environment variables"
            logger.error(error_msg)
            return {"error": error_msg}
        
        if not TOKEN_CUSTOM_LLM:
            error_msg = "TOKEN_CUSTOM_LLM_APILOGY not found in environment variables"
            logger.error(error_msg)
            return {"error": error_msg}

        # API endpoint and payload setup
        url = URL_CUSTOM_LLM
        token = TOKEN_CUSTOM_LLM
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": extraction_prompt.format(
                        ocr_result=ocr_result
                    ),
                }
            ],
            "max_tokens": 20000,
            "temperature": 0,
            "stream": False
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": token
        }
        
        logger.debug(f"Making request to: {url}")
        logger.debug(f"Payload keys: {list(payload.keys())}")
        
        timeout = httpx.Timeout(60.0)  # 60 second timeout
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
        
        logger.debug(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            if 'choices' in response_data and len(response_data['choices']) > 0:
                return response_data['choices'][0]['message']['content']
            else:
                error_msg = f"Unexpected response structure: {response_data}"
                logger.error(error_msg)
                return {"error": error_msg}
        else:
            error_message = response.text
            logger.error(f"API Error {response.status_code}: {error_message}")
            return {"error": f"API call failed with status {response.status_code}: {error_message}"}
            
    except httpx.TimeoutException as e:
        error_msg = f"Request timeout: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
    except httpx.RequestError as e:
        error_msg = f"Request error: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
    except json.JSONDecodeError as e:
        error_msg = f"JSON decode error: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error in telkomllm_call_ocr: {type(e).__name__}: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

async def telkommultimodal_call(extraction_prompt, img_base64):
    """
    Makes an asynchronous API call to the Telkom Multimodal API.
    """
    try:
        # Validate environment variables
        if not URL_CUSTOM_LMM:
            error_msg = "URL_CUSTOM_LMM not found in environment variables"
            logger.error(error_msg)
            return {"error": error_msg}
        
        if not TOKEN_CUSTOM_LMM:
            error_msg = "TOKEN_CUSTOM_LMM not found in environment variables"
            logger.error(error_msg)
            return {"error": error_msg}

        # API endpoint and payload setup
        url = URL_CUSTOM_LMM
        token = TOKEN_CUSTOM_LMM
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": token
        }

        data = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": extraction_prompt,
                            "type": "text"
                        },
                        {
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}"
                            },
                            "type": "image_url"
                        }
                    ]
                }
            ],
            "max_tokens": 3000,
            "temperature": 0,
            "stream": False
        }
        
        logger.debug(f"Making request to: {url}")
        logger.debug(f"Image data length: {len(img_base64) if img_base64 else 0}")
        
        timeout = httpx.Timeout(60.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=data, headers=headers)
        
        logger.debug(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            if 'choices' in response_data and len(response_data['choices']) > 0:
                return response_data['choices'][0]['message']['content']
            else:
                error_msg = f"Unexpected response structure: {response_data}"
                logger.error(error_msg)
                return {"error": error_msg}
        else:
            error_message = response.text
            logger.error(f"API Error {response.status_code}: {error_message}")
            return {"error": f"API call failed with status {response.status_code}: {error_message}"}
            
    except httpx.TimeoutException as e:
        error_msg = f"Request timeout: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
    except httpx.RequestError as e:
        error_msg = f"Request error: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
    except json.JSONDecodeError as e:
        error_msg = f"JSON decode error: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error in telkommultimodal_call: {type(e).__name__}: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

async def telkommnanonets_call(img_base64):
    """
    Makes an asynchronous API call to the Telkom Nanonets API.
    """
    try:
        # Validate environment variables
        if not URL_CUSTOM_NANONETS:
            error_msg = "URL_CUSTOM_NANONETS not found in environment variables"
            logger.error(error_msg)
            return {"error": error_msg}
        
        if not TOKEN_CUSTOM_NANONETS:
            error_msg = "TOKEN_CUSTOM_NANONETS not found in environment variables"
            logger.error(error_msg)
            return {"error": error_msg}

        url = URL_CUSTOM_NANONETS
        token = TOKEN_CUSTOM_NANONETS
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": token
        }
        data = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}"
                            },
                            "type": "image_url"
                        }
                    ]
                }
            ],
            "model": "telkom-document-extraction-multimodal",
            "max_tokens": 2000,
            "temperature": 0,
            "stream": False
        }
        
        logger.debug(f"Making request to: {url}")
        logger.debug(f"Image data length: {len(img_base64) if img_base64 else 0}")
        
        timeout = httpx.Timeout(60.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=data, headers=headers)
            
        logger.debug(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            if 'choices' in response_data and len(response_data['choices']) > 0:
                return response_data['choices'][0]['message']['content']
            else:
                error_msg = f"Unexpected response structure: {response_data}"
                logger.error(error_msg)
                return {"error": error_msg}
        else:
            error_message = response.text
            logger.error(f"API Error {response.status_code}: {error_message}")
            return {"error": f"API call failed with status {response.status_code}: {error_message}"}
            
    except httpx.TimeoutException as e:
        error_msg = f"Request timeout: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
    except httpx.RequestError as e:
        error_msg = f"Request error: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
    except json.JSONDecodeError as e:
        error_msg = f"JSON decode error: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error in telkommnanonets_call: {type(e).__name__}: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}