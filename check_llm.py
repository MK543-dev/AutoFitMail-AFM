"""Quick check of the AI settings in .env.

Works with:
- provider 'anthropic' -> Anthropic API, or any Anthropic-Messages-compatible
  gateway (e.g. AshnaAI https://api.ashna.ai/v1/api)
- provider 'gemini'    -> Google AI Studio / Gemini API

Run inside afm/:   python check_llm.py [model]

It reads afm/.env directly (no Django), sends a tiny "ping" message and
prints the exact HTTP result, including a plain-language hint on failures.
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote


def load_env():
    env = {}
    env_path = Path(__file__).resolve().parent / '.env'
    for line in env_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            env[key.strip()] = value.strip()
    return env


def error_hints(code, detail):
    if code in (401, 403):
        if 'denied access' in detail.lower():
            print('-> Google has denied access for this project. Create a NEW API key in a')
            print('   NEW project (https://aistudio.google.com/apikey), or contact Google')
            print('   support - this is a project-level block, not a quota issue.')
        else:
            print('-> Key rejected or not allowed. Check the API key (was it rotated?).')
    elif code == 404:
        print('-> Unknown or retired model id. The error text usually names the current one')
        print('   (Google now recommends gemini-3.8-flash). Check GEMINI_MODEL / ANTHROPIC_MODEL.')
    elif code == 503:
        print('-> Model temporarily overloaded ("high demand"). Wait a few minutes and retry.')
    elif code == 429:
        if 'paid plan' in detail.lower():
            print('-> Ashna free plans cannot fund external API calls; this needs their')
            print('   paid plan (https://app.ashna.ai/pricing) or a different provider.')
        else:
            print('-> Rate limit / quota. Wait a bit or use a lighter model.')
    elif code == 400:
        print('-> Bad request: check the model id and that the key belongs to this API.')


def main():
    env = load_env()
    provider = (env.get('LLM_PROVIDER', '') or 'anthropic').lower()
    model_arg = sys.argv[1] if len(sys.argv) > 1 else None

    if provider == 'gemini':
        api_key = env.get('GEMINI_API_KEY', '')
        base = (env.get('GEMINI_BASE_URL', '') or 'https://generativelanguage.googleapis.com/v1beta').rstrip('/')
        model = model_arg or env.get('GEMINI_MODEL', 'gemini-2.5-flash')
        if not api_key:
            print('No GEMINI_API_KEY found in .env - add your key first'
                  ' (free key: https://aistudio.google.com/apikey).')
            sys.exit(1)
        url = f'{base}/models/{model}:generateContent?key={quote(api_key)}'
        print(f'POST {base}/models/{model}:generateContent')
        print(f'provider: gemini | model: {model}')
        body = json.dumps({
            'contents': [{'role': 'user', 'parts': [{'text': 'Reply with exactly: ping'}]}],
            'generationConfig': {'maxOutputTokens': 16},
        }).encode('utf-8')
        req = urllib.request.Request(url, data=body, method='POST')
        req.add_header('content-type', 'application/json')
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                status = resp.status
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode('utf-8', 'replace')[:400]
            print(f'HTTP error {exc.code}: {detail}')
            error_hints(exc.code, detail)
            sys.exit(1)
        except Exception as exc:  # noqa: BLE001
            print(f'Connection problem: {type(exc).__name__}: {exc}')
            sys.exit(1)
        parts = ((data.get('candidates') or [{}])[0].get('content') or {}).get('parts') or []
        text = ''.join(p.get('text', '') for p in parts)
        print('HTTP', status)
        print('reply:', text.strip())
        print('Everything works: AFM can generate with these settings.')
        return

    api_key = env.get('ANTHROPIC_API_KEY', '')
    base_url = (env.get('ANTHROPIC_BASE_URL', '') or 'https://api.anthropic.com').rstrip('/')
    model = model_arg or env.get('ANTHROPIC_MODEL', 'claude-sonnet-4.5')
    if not api_key:
        print('No ANTHROPIC_API_KEY found in .env - add your key first.')
        sys.exit(1)
    url = f'{base_url}/v1/messages'
    print(f'POST {url}')
    print(f'provider: anthropic | model: {model}')
    body = json.dumps({
        'model': model,
        'max_tokens': 16,
        'messages': [{'role': 'user', 'content': 'Reply with exactly: ping'}],
    }).encode('utf-8')
    req = urllib.request.Request(url, data=body, method='POST')
    req.add_header('content-type', 'application/json')
    req.add_header('anthropic-version', '2023-06-01')
    req.add_header('x-api-key', api_key)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            status = resp.status
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', 'replace')[:400]
        print(f'HTTP error {exc.code}: {detail}')
        error_hints(exc.code, detail)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f'Connection problem: {type(exc).__name__}: {exc}')
        sys.exit(1)
    text = ''.join(b.get('text', '') for b in data.get('content', []) if b.get('type') == 'text')
    print('HTTP', status)
    print('reply:', text.strip())
    print('Everything works: AFM can generate with these settings.')


if __name__ == '__main__':
    main()
