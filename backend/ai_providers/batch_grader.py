"""
BATCH GRADING MODULE - 50% COST SAVINGS
Uses Together.AI Batch API for bulk comic grading

Authority Level: 11.0
Commander: Bobby Don McWilliams II
"""

import asyncio
import aiohttp
import json
import logging
import os
import re
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

# Load .env file
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        load_dotenv(env_file, override=True)
except ImportError:
    pass

# Import from together_grader
try:
    from .together_grader import GRADING_PROMPT, get_grade_label, extract_grade_from_text, PRIMARY_MODEL, grade_with_together
except ImportError:
    from ai_providers.together_grader import GRADING_PROMPT, get_grade_label, extract_grade_from_text, PRIMARY_MODEL, grade_with_together


def get_api_key() -> Optional[str]:
    """Get Together AI API key from environment"""
    return os.environ.get('TOGETHER_API_KEY')


async def batch_grade_comics(
    comics: List[Dict[str, Any]],
    model: str = None,
    wait_for_completion: bool = True,
    max_wait_seconds: int = 300
) -> List[Dict[str, Any]]:
    """
    Batch grade multiple comics for 50% cost savings

    Uses Together.AI Batch API for async processing with
    significant cost reduction.

    Args:
        comics: List of dicts with 'image_data', 'title', 'issue' keys
        model: Model to use (default: Llama-4-Scout)
        wait_for_completion: Wait for batch to complete
        max_wait_seconds: Maximum wait time

    Returns:
        List of grading results
    """
    model = model or PRIMARY_MODEL
    api_key = get_api_key()

    if not api_key:
        logger.error("TOGETHER_API_KEY not found")
        return [{"error": "No API key", "grade": 0} for _ in comics]

    try:
        from .base64_utils import clean_and_validate_base64
    except ImportError:
        from ai_providers.base64_utils import clean_and_validate_base64

    results = []
    batch_requests = []

    # Prepare batch requests
    for i, comic in enumerate(comics):
        clean_base64, error = clean_and_validate_base64(comic.get('image_data', ''))
        if error:
            results.append({
                'index': i,
                'error': f'Image error: {error}',
                'grade': 0,
                'provider': 'Together_Batch'
            })
            continue

        request = {
            "custom_id": f"comic_{i}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": GRADING_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{clean_base64}"}
                            }
                        ]
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 1500
            }
        }
        batch_requests.append(request)

    if not batch_requests:
        return results

    logger.info(f"Starting batch job for {len(batch_requests)} comics...")

    try:
        async with aiohttp.ClientSession() as session:
            # Create batch file content
            batch_file_content = "\n".join(json.dumps(r) for r in batch_requests)

            # Upload batch file
            form_data = aiohttp.FormData()
            form_data.add_field(
                'file',
                batch_file_content.encode(),
                filename='batch.jsonl',
                content_type='application/jsonl'
            )
            form_data.add_field('purpose', 'batch')

            async with session.post(
                "https://api.together.xyz/v1/files",
                headers={"Authorization": f"Bearer {api_key}"},
                data=form_data,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Batch file upload failed: {error_text}")
                    return await _fallback_individual_grading(comics, model)

                file_data = await resp.json()
                file_id = file_data.get('id')
                logger.info(f"Batch file uploaded: {file_id}")

            # Create batch job
            async with session.post(
                "https://api.together.xyz/v1/batches",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "input_file_id": file_id,
                    "endpoint": "/v1/chat/completions",
                    "completion_window": "24h"
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Batch creation failed: {error_text}")
                    return await _fallback_individual_grading(comics, model)

                batch_data = await resp.json()
                batch_id = batch_data.get('id')
                logger.info(f"Batch job created: {batch_id} (50% cost savings!)")

            if not wait_for_completion:
                return [{
                    'batch_id': batch_id,
                    'status': 'submitted',
                    'message': 'Batch submitted. Check status later.',
                    'comics_count': len(batch_requests)
                }]

            # Poll for completion
            poll_interval = 5
            elapsed = 0
            output_file_id = None

            while elapsed < max_wait_seconds:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

                async with session.get(
                    f"https://api.together.xyz/v1/batches/{batch_id}",
                    headers={"Authorization": f"Bearer {api_key}"}
                ) as resp:
                    if resp.status == 200:
                        status_data = await resp.json()
                        status = status_data.get('status')

                        if status == 'completed':
                            output_file_id = status_data.get('output_file_id')
                            logger.info(f"Batch completed in {elapsed}s")
                            break
                        elif status in ('failed', 'cancelled', 'expired'):
                            logger.error(f"Batch job {status}")
                            return await _fallback_individual_grading(comics, model)

                        logger.info(f"Batch status: {status} ({elapsed}s/{max_wait_seconds}s)")

            else:
                logger.warning("Batch timeout - falling back to individual grading")
                return await _fallback_individual_grading(comics, model)

            # Download results
            async with session.get(
                f"https://api.together.xyz/v1/files/{output_file_id}/content",
                headers={"Authorization": f"Bearer {api_key}"}
            ) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    for line in content.strip().split('\n'):
                        if line:
                            result = json.loads(line)
                            custom_id = result.get('custom_id', '')
                            idx = int(custom_id.split('_')[1]) if '_' in custom_id else 0

                            response_body = result.get('response', {}).get('body', {})
                            message_content = response_body.get('choices', [{}])[0].get('message', {}).get('content', '')

                            # Parse grading result
                            try:
                                json_match = re.search(r'\{[\s\S]*\}', message_content)
                                if json_match:
                                    grading_data = json.loads(json_match.group())
                                    grade = float(grading_data.get('grade', 6.0))
                                    grade = max(0.5, min(10.0, round(grade * 2) / 2))

                                    results.append({
                                        'index': idx,
                                        'grade': grade,
                                        'grade_label': grading_data.get('grade_label', get_grade_label(grade)),
                                        'confidence': float(grading_data.get('confidence', 0.8)),
                                        'defects': grading_data.get('defects', []),
                                        'reasoning': grading_data.get('reasoning', ''),
                                        'comic_info': grading_data.get('comic_info', {}),
                                        'model': model,
                                        'provider': 'Together_Batch',
                                        'icon': '🦙',
                                        'batch_savings': '50%'
                                    })
                            except json.JSONDecodeError:
                                grade = extract_grade_from_text(message_content)
                                results.append({
                                    'index': idx,
                                    'grade': grade,
                                    'grade_label': get_grade_label(grade),
                                    'confidence': 0.7,
                                    'provider': 'Together_Batch'
                                })

            # Sort by index
            results.sort(key=lambda x: x.get('index', 0))
            logger.info(f"Batch complete: {len(results)} comics graded with 50% savings!")
            return results

    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        import traceback
        traceback.print_exc()
        return await _fallback_individual_grading(comics, model)


async def _fallback_individual_grading(
    comics: List[Dict[str, Any]],
    model: str
) -> List[Dict[str, Any]]:
    """Fall back to individual grading if batch fails"""
    logger.info("Falling back to individual grading...")
    results = []

    for i, comic in enumerate(comics):
        result = await grade_with_together(
            image_input=comic.get('image_data', ''),
            model=model,
            metadata={'title': comic.get('title', ''), 'issue': comic.get('issue', '')}
        )
        result['index'] = i
        results.append(result)

    return results


async def check_batch_status(batch_id: str) -> Dict[str, Any]:
    """Check status of a batch job"""
    api_key = get_api_key()
    if not api_key:
        return {"error": "No API key"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.together.xyz/v1/batches/{batch_id}",
                headers={"Authorization": f"Bearer {api_key}"}
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    return {"error": f"Status check failed: {resp.status}"}
    except Exception as e:
        return {"error": str(e)}


__all__ = [
    'batch_grade_comics',
    'check_batch_status',
]
