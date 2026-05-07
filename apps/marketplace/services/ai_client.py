"""Client for the external AI API (Flask service on a separate port)."""

import base64
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _base_url():
    return getattr(settings, 'AI_API_BASE_URL', 'http://localhost:5000').rstrip('/')


def _timeout():
    return getattr(settings, 'AI_API_TIMEOUT', 5)


def _post(path, payload):
    """POST JSON to the AI API. Returns parsed response or None on failure."""
    url = f'{_base_url()}{path}'
    try:
        resp = requests.post(url, json=payload, timeout=_timeout())
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        logger.warning('AI API unreachable at %s', url)
    except requests.Timeout:
        logger.warning('AI API timed out at %s', url)
    except requests.HTTPError as exc:
        logger.warning('AI API error: %s', exc)
    except (ValueError, KeyError) as exc:
        logger.warning('AI API bad response: %s', exc)
    return None


def get_suggestions(customer_id, top_n=5):
    """Reorder predictions — returns [{"product": ..., "score": ...}] or None."""
    data = _post('/predict/reorder', {
        'customer_id': 'CUST001',  
        'top_n': top_n,
    })
    if data and 'suggestions' in data:
        return data['suggestions']
    return None


def check_quality(image_bytes):
    """Quality grading — accepts raw image bytes, returns grading dict or None."""
    encoded = base64.b64encode(image_bytes).decode('ascii')
    return _post('/predict/quality', {'image': encoded})