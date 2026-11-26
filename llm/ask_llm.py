#!/usr/bin/env python3
"""Send a prompt and the code bundle to an LLM through its API and save the answer.

Supported providers: openai (OPENAI_API_KEY), anthropic (ANTHROPIC_API_KEY), and
ollama: Ollama's native API, with an explicit context size (--num-ctx), because
Ollama otherwise truncates long prompts silently to its small default window;
local: any OpenAI-compatible server (vLLM, Ollama, llama.cpp) given by --base-url,
e.g. http://localhost:8000/v1 for vLLM or http://localhost:11434/v1 for Ollama.
The code bundle is sent inline, before the prompt. Temperature is set to 0
where the model allows it. Each call is logged with the model name and time,
so the experiment can be reported precisely.

Usage:
    python3 ask_llm.py --provider openai --model <model-name> \
        --bundle pack_rnaseq/code_bundle.txt \
        --prompt pack_rnaseq/prompts/R01_hisat2/end_to_end.md -o answers/openai/R01_end_to_end.json
"""
import argparse
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request


def post(url, headers, body, attempts=5):
    """POST with retries on rate limits, server errors and dropped connections."""
    data = json.dumps(body).encode()
    for i in range(attempts):
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=7200) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors='replace')[:500]
            if e.code not in (408, 409, 429, 500, 502, 503, 504, 529) or i == attempts - 1:
                raise SystemExit(f'HTTP {e.code} from {url}: {detail}')
            print(f'HTTP {e.code}, retrying in {30 * 2 ** i} s: {detail[:120]}')
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if i == attempts - 1:
                raise SystemExit(f'Connection error to {url}: {e}')
            print(f'Connection error, retrying in {30 * 2 ** i} s: {e}')
        time.sleep(30 * 2 ** i)


def ask_openai(model, text, temperature):
    body = {'model': model, 'input': text}
    if temperature is not None:
        body['temperature'] = temperature
    data = post('https://api.openai.com/v1/responses',
                {'Authorization': f'Bearer {os.environ["OPENAI_API_KEY"]}', 'Content-Type': 'application/json'},
                body)
    parts = [c.get('text', '') for item in data.get('output', []) for c in item.get('content', []) or []]
    return ''.join(parts), data


def ask_anthropic(model, text, temperature, split=None):
    # The bundle is a separate content block marked for prompt caching, so that
    # repeated calls with the same bundle are billed at the cached-input rate.
    if split:
        content = [{'type': 'text', 'text': split[0], 'cache_control': {'type': 'ephemeral'}},
                   {'type': 'text', 'text': split[1]}]
    else:
        content = text
    body = {'model': model, 'max_tokens': 8000, 'messages': [{'role': 'user', 'content': content}]}
    if temperature is not None:
        body['temperature'] = temperature
    data = post('https://api.anthropic.com/v1/messages',
                {'x-api-key': os.environ['ANTHROPIC_API_KEY'], 'anthropic-version': '2023-06-01',
                 'content-type': 'application/json'},
                body)
    return ''.join(b.get('text', '') for b in data.get('content', [])), data


def ask_local(model, text, temperature, base_url, max_tokens=8000):
    body = {'model': model, 'max_tokens': max_tokens, 'messages': [{'role': 'user', 'content': text}]}
    if temperature is not None:
        body['temperature'] = temperature
    headers = {'Content-Type': 'application/json'}
    if os.environ.get('LOCAL_API_KEY'):
        headers['Authorization'] = f'Bearer {os.environ["LOCAL_API_KEY"]}'
    data = post(base_url.rstrip('/') + '/chat/completions', headers, body)
    return data['choices'][0]['message'].get('content') or '', data


def ask_ollama(model, text, temperature, base_url, num_ctx):
    options = {'num_ctx': num_ctx}
    if temperature is not None:
        options['temperature'] = temperature
    body = {'model': model, 'stream': False, 'options': options,
            'messages': [{'role': 'user', 'content': text}]}
    data = post(base_url.rstrip('/') + '/api/chat', {'Content-Type': 'application/json'}, body)
    used = data.get('prompt_eval_count')
    if used is not None and used >= num_ctx - 16:
        print(f'WARNING: prompt used {used} tokens of a {num_ctx}-token window; it was probably truncated')
    return data['message'].get('content') or '', data


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--provider', choices=['openai', 'anthropic', 'local', 'ollama'], required=True)
    ap.add_argument('--model', required=True)
    ap.add_argument('--bundle', required=True)
    ap.add_argument('--prompt', required=True)
    ap.add_argument('--temperature', type=float, default=0.0)
    ap.add_argument('--no-temperature', action='store_true', help='omit temperature (for models that reject it)')
    ap.add_argument('--base-url', default=None, help='server URL (default http://localhost:8000/v1 for local, http://localhost:11434 for ollama)')
    ap.add_argument('--num-ctx', type=int, default=65536, help='context window for --provider ollama')
    ap.add_argument('-o', '--output', required=True)
    args = ap.parse_args()

    code = open(args.bundle, encoding='utf-8').read()
    prompt = open(args.prompt, encoding='utf-8').read()
    text = f'===== Attached file: code_bundle.txt =====\n{code}\n===== End of code_bundle.txt =====\n\n{prompt}'
    temperature = None if args.no_temperature else args.temperature

    try:
        if args.provider == 'local':
            answer, raw = ask_local(args.model, text, temperature, args.base_url or 'http://localhost:8000/v1')
        elif args.provider == 'ollama':
            answer, raw = ask_ollama(args.model, text, temperature, args.base_url or 'http://localhost:11434', args.num_ctx)
        elif args.provider == 'anthropic':
            head = f'===== Attached file: code_bundle.txt =====\n{code}\n===== End of code_bundle.txt =====\n\n'
            answer, raw = ask_anthropic(args.model, text, temperature, split=(head, prompt))
        else:
            answer, raw = ask_openai(args.model, text, temperature)
    except KeyError as e:
        sys.exit(f'Missing API key in environment: {e}')

    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    open(args.output, 'w', encoding='utf-8').write(answer)
    json.dump({'provider': args.provider, 'model': args.model, 'base_url': args.base_url, 'num_ctx': args.num_ctx if args.provider == 'ollama' else None, 'prompt': args.prompt,
               'temperature': temperature, 'time': datetime.datetime.now().isoformat(),
               'usage': raw.get('usage') or {k: raw.get(k) for k in ('prompt_eval_count', 'eval_count', 'total_duration')}},
              open(args.output + '.meta.json', 'w'), indent=2)
    print(f'answer saved to {args.output}')


if __name__ == '__main__':
    main()
