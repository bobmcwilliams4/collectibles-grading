"""
API Provider Test Script - UPDATED
Tests each AI provider API to verify connectivity and valid responses
Fixed: Updated models and endpoints for 2025
"""
import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def test_gemini():
    print('\n' + '='*60)
    print('TESTING: Google Gemini')
    print('='*60)
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print('ERROR: No API key found')
        return False

    # Try gemini-2.0-flash first (newest)
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}'
    payload = {
        'contents': [{
            'parts': [
                {'text': 'Say hello in exactly 5 words'}
            ]
        }]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                status = resp.status
                data = await resp.json()
                if status == 200:
                    text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'No text')
                    print(f'STATUS: {status} - SUCCESS')
                    print(f'RESPONSE: {text[:200]}')
                    return True
                else:
                    print(f'STATUS: {status} - FAILED')
                    print(f'ERROR: {json.dumps(data, indent=2)[:300]}')
                    return False
    except Exception as e:
        print(f'EXCEPTION: {str(e)}')
        return False

async def test_groq():
    print('\n' + '='*60)
    print('TESTING: Groq')
    print('='*60)
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        print('ERROR: No API key found')
        return False

    url = 'https://api.groq.com/openai/v1/chat/completions'
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    payload = {
        'model': 'llama-3.3-70b-versatile',  # Updated model
        'messages': [{'role': 'user', 'content': 'Say hello in exactly 5 words'}],
        'max_tokens': 50
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                status = resp.status
                data = await resp.json()
                if status == 200:
                    text = data.get('choices', [{}])[0].get('message', {}).get('content', 'No text')
                    print(f'STATUS: {status} - SUCCESS')
                    print(f'RESPONSE: {text[:200]}')
                    return True
                else:
                    print(f'STATUS: {status} - FAILED')
                    print(f'ERROR: {json.dumps(data, indent=2)[:300]}')
                    return False
    except Exception as e:
        print(f'EXCEPTION: {str(e)}')
        return False

async def test_deepseek():
    print('\n' + '='*60)
    print('TESTING: DeepSeek')
    print('='*60)
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        print('ERROR: No API key found')
        return False

    url = 'https://api.deepseek.com/chat/completions'
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    payload = {
        'model': 'deepseek-chat',
        'messages': [{'role': 'user', 'content': 'Say hello in exactly 5 words'}],
        'max_tokens': 50
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                status = resp.status
                data = await resp.json()
                if status == 200:
                    text = data.get('choices', [{}])[0].get('message', {}).get('content', 'No text')
                    print(f'STATUS: {status} - SUCCESS')
                    print(f'RESPONSE: {text[:200]}')
                    return True
                else:
                    print(f'STATUS: {status} - FAILED')
                    print(f'ERROR: {json.dumps(data, indent=2)[:300]}')
                    return False
    except Exception as e:
        print(f'EXCEPTION: {str(e)}')
        return False

async def test_xai_grok():
    print('\n' + '='*60)
    print('TESTING: xAI Grok')
    print('='*60)
    api_key = os.getenv('XAI_API_KEY')
    if not api_key:
        print('ERROR: No API key found')
        return False

    url = 'https://api.x.ai/v1/chat/completions'
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    payload = {
        'model': 'grok-3',  # Updated from deprecated grok-beta
        'messages': [{'role': 'user', 'content': 'Say hello in exactly 5 words'}],
        'max_tokens': 50
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                status = resp.status
                data = await resp.json()
                if status == 200:
                    text = data.get('choices', [{}])[0].get('message', {}).get('content', 'No text')
                    print(f'STATUS: {status} - SUCCESS')
                    print(f'RESPONSE: {text[:200]}')
                    return True
                else:
                    print(f'STATUS: {status} - FAILED')
                    print(f'ERROR: {json.dumps(data, indent=2)[:300]}')
                    return False
    except Exception as e:
        print(f'EXCEPTION: {str(e)}')
        return False

async def test_openrouter():
    print('\n' + '='*60)
    print('TESTING: OpenRouter')
    print('='*60)
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print('ERROR: No API key found')
        return False

    url = 'https://openrouter.ai/api/v1/chat/completions'
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    payload = {
        'model': 'google/gemini-2.0-flash-exp:free',
        'messages': [{'role': 'user', 'content': 'Say hello in exactly 5 words'}],
        'max_tokens': 50
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                status = resp.status
                data = await resp.json()
                if status == 200:
                    text = data.get('choices', [{}])[0].get('message', {}).get('content', 'No text')
                    print(f'STATUS: {status} - SUCCESS')
                    print(f'RESPONSE: {text[:200]}')
                    return True
                else:
                    print(f'STATUS: {status} - FAILED')
                    print(f'ERROR: {json.dumps(data, indent=2)[:300]}')
                    return False
    except Exception as e:
        print(f'EXCEPTION: {str(e)}')
        return False

async def test_cohere():
    print('\n' + '='*60)
    print('TESTING: Cohere')
    print('='*60)
    api_key = os.getenv('COHERE_API_KEY')
    if not api_key:
        print('ERROR: No API key found')
        return False

    url = 'https://api.cohere.ai/v1/chat'
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    payload = {
        'model': 'command-r-plus',  # Updated from deprecated command-r
        'message': 'Say hello in exactly 5 words'
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                status = resp.status
                data = await resp.json()
                if status == 200:
                    text = data.get('text', 'No text')
                    print(f'STATUS: {status} - SUCCESS')
                    print(f'RESPONSE: {text[:200]}')
                    return True
                else:
                    print(f'STATUS: {status} - FAILED')
                    print(f'ERROR: {json.dumps(data, indent=2)[:300]}')
                    return False
    except Exception as e:
        print(f'EXCEPTION: {str(e)}')
        return False

async def test_perplexity():
    print('\n' + '='*60)
    print('TESTING: Perplexity')
    print('='*60)
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        print('ERROR: No API key found')
        return False

    url = 'https://api.perplexity.ai/chat/completions'
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    payload = {
        'model': 'sonar',  # Updated model name
        'messages': [{'role': 'user', 'content': 'Say hello in exactly 5 words'}],
        'max_tokens': 50
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                status = resp.status
                try:
                    data = await resp.json()
                except:
                    text = await resp.text()
                    print(f'STATUS: {status} - FAILED (non-JSON response)')
                    print(f'RAW: {text[:300]}')
                    return False

                if status == 200:
                    text = data.get('choices', [{}])[0].get('message', {}).get('content', 'No text')
                    print(f'STATUS: {status} - SUCCESS')
                    print(f'RESPONSE: {text[:200]}')
                    return True
                else:
                    print(f'STATUS: {status} - FAILED')
                    print(f'ERROR: {json.dumps(data, indent=2)[:300]}')
                    return False
    except Exception as e:
        print(f'EXCEPTION: {str(e)}')
        return False

async def test_huggingface():
    print('\n' + '='*60)
    print('TESTING: HuggingFace (router)')
    print('='*60)
    api_key = os.getenv('HUGGINGFACE_API_KEY')
    if not api_key:
        print('ERROR: No API key found')
        return False

    # Updated endpoint
    url = 'https://router.huggingface.co/hf-inference/models/microsoft/Phi-3-mini-4k-instruct/v1/chat/completions'
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    payload = {
        'messages': [{'role': 'user', 'content': 'Say hello in exactly 5 words'}],
        'max_tokens': 50
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                status = resp.status
                try:
                    data = await resp.json()
                except:
                    text = await resp.text()
                    print(f'STATUS: {status} - response: {text[:200]}')
                    return status == 200

                if status == 200:
                    if 'choices' in data:
                        text = data.get('choices', [{}])[0].get('message', {}).get('content', 'No text')
                    else:
                        text = str(data)[:200]
                    print(f'STATUS: {status} - SUCCESS')
                    print(f'RESPONSE: {text[:200]}')
                    return True
                else:
                    print(f'STATUS: {status} - FAILED')
                    print(f'ERROR: {json.dumps(data, indent=2)[:300]}')
                    return False
    except Exception as e:
        print(f'EXCEPTION: {str(e)}')
        return False

async def test_replicate():
    print('\n' + '='*60)
    print('TESTING: Replicate')
    print('='*60)
    api_key = os.getenv('REPLICATE_API_TOKEN')
    if not api_key:
        print('ERROR: No API key found')
        return False

    url = 'https://api.replicate.com/v1/models'
    headers = {'Authorization': f'Bearer {api_key}'}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                status = resp.status
                if status == 200:
                    print(f'STATUS: {status} - SUCCESS (API key valid)')
                    return True
                else:
                    data = await resp.json()
                    print(f'STATUS: {status} - FAILED')
                    print(f'ERROR: {json.dumps(data, indent=2)[:300]}')
                    return False
    except Exception as e:
        print(f'EXCEPTION: {str(e)}')
        return False

async def test_elevenlabs():
    print('\n' + '='*60)
    print('TESTING: ElevenLabs')
    print('='*60)
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        print('ERROR: No API key found')
        return False

    url = 'https://api.elevenlabs.io/v1/user'
    headers = {'xi-api-key': api_key}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                status = resp.status
                data = await resp.json()
                if status == 200:
                    print(f'STATUS: {status} - SUCCESS')
                    print(f'USER: {data.get("subscription", {}).get("tier", "Unknown tier")}')
                    return True
                else:
                    print(f'STATUS: {status} - FAILED')
                    print(f'ERROR: {json.dumps(data, indent=2)[:300]}')
                    return False
    except Exception as e:
        print(f'EXCEPTION: {str(e)}')
        return False

async def main():
    print('\n' + '#'*60)
    print('  AI PROVIDER API VALIDATION TEST')
    print('  Testing each API directly (UPDATED)')
    print('#'*60)

    results = {}

    results['Gemini'] = await test_gemini()
    results['Groq'] = await test_groq()
    results['DeepSeek'] = await test_deepseek()
    results['xAI Grok'] = await test_xai_grok()
    results['OpenRouter'] = await test_openrouter()
    results['Cohere'] = await test_cohere()
    results['Perplexity'] = await test_perplexity()
    results['HuggingFace'] = await test_huggingface()
    results['Replicate'] = await test_replicate()
    results['ElevenLabs'] = await test_elevenlabs()

    print('\n' + '#'*60)
    print('  FINAL RESULTS')
    print('#'*60)

    passed = 0
    failed = 0
    for name, success in results.items():
        status = 'PASS' if success else 'FAIL'
        emoji = '[OK]' if success else '[X]'
        print(f'{emoji} {name}: {status}')
        if success:
            passed += 1
        else:
            failed += 1

    print(f'\nTOTAL: {passed}/{len(results)} APIs working')

    print('\n' + '#'*60)
    print('  VISION-CAPABLE APIs FOR GRADING')
    print('#'*60)
    vision_apis = ['Gemini', 'OpenRouter', 'xAI Grok', 'DeepSeek']
    vision_working = sum(1 for api in vision_apis if results.get(api, False))
    print(f'Vision APIs working: {vision_working}/{len(vision_apis)}')
    for api in vision_apis:
        emoji = '[OK]' if results.get(api, False) else '[X]'
        print(f'  {emoji} {api}')

if __name__ == '__main__':
    asyncio.run(main())
