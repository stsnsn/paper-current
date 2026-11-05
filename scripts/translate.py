"""Incremental, resumable translation using LM Studio and PLaMo PFML3."""
import argparse
import datetime as dt
import hashlib
import os
from pathlib import Path
import requests
from common import load, write, dedupe_records

FORMAT = 'pfml3-ja-v1'

def fingerprint(text, model):
    return hashlib.sha256((text+'|'+model+'|'+FORMAT).encode()).hexdigest()

def utcnow():
    return dt.datetime.now(dt.timezone.utc)

class Translator:
    def __init__(self, base_url='http://localhost:1234/v1', model=None, max_tokens=4096):
        self.base = base_url.rstrip('/')
        self.session = requests.Session()
        # localhost must not be sent through a configured HTTP proxy.
        self.session.trust_env = False
        token = os.getenv('LM_STUDIO_API_KEY')
        if token:
            self.session.headers['Authorization'] = 'Bearer '+token
        self.max_tokens = max_tokens
        self.model = model

    def connect(self):
        r = self.session.get(self.base+'/models', timeout=15)
        r.raise_for_status()
        ids = [a['id'] for a in r.json()['data']]
        if self.model:
            if self.model not in ids:
                raise RuntimeError('Configured model is not available in LM Studio: '+self.model)
        else:
            choices = [a for a in ids if 'plamo' in a.lower()]
            if len(choices) != 1:
                raise RuntimeError('Set --model to an exact PLaMo model ID. Available: '+str(ids))
            self.model = choices[0]
        return self

    def translate(self, source):
        if '<|plamo:' in source:
            raise ValueError('Unexpected special token in source')
        prompt = ('<|plamo:tag|>dataset<|plamo:msg|>translation'
                  '<|plamo:tag|>input<|plamo:key|>lang<|plamo:val|>en<|plamo:msg|>'
                  + source + '<|plamo:tag|>output<|plamo:key|>lang<|plamo:val|>ja'
                  '<|plamo:key|>form<|plamo:val|>plain<|plamo:msg|>')
        r = self.session.post(self.base+'/completions', json={
            'model': self.model, 'prompt': prompt, 'temperature': 0,
            'max_tokens': self.max_tokens,
            'stop': ['<|plamo:tag|>', '<|plamo:bos|>'], 'stream': False,
        }, timeout=600)
        r.raise_for_status()
        choice = r.json()['choices'][0]
        if choice.get('finish_reason') == 'length':
            raise RuntimeError('Translation truncated; increase max_tokens')
        value = choice['text'].strip()
        if not value or '<|plamo:' in value:
            raise RuntimeError('Empty or malformed translation')
        return value

def translate_records(rows, output, translator, *, limit=0, force=False,
                      keep_going=False, retry_state=None, now=None, include_pending=False, on_progress=None):
    """Checkpoint every field. Failed abstracts never discard finished titles."""
    now = now or utcnow()
    rows=dedupe_records(rows)
    previous = {a['id']: a for a in dedupe_records(load(output, []))}
    retries = load(retry_state, {}) if retry_state else {}
    stats = dict(translated=0, cached=0, failed=0, deferred=0, skipped=0, requests=0)
    attempted = 0
    for row in rows:
        permitted = row.get('rights_status') == 'allowed' or (include_pending and row.get('rights_status') == 'pending')
        if not permitted or not row.get('title') or (not row.get('abstract') and not include_pending):
            # Metadata/rights may change after translation. Retain history, but
            # do not allow an old 'allowed' flag to leak into a new issue.
            if row['id'] in previous:
                previous[row['id']] = {**previous[row['id']], **row}
                write(output, list(previous.values()))
            stats['skipped'] += 1
            continue
        old = previous.get(row['id'], {})
        record = {**row, 'translation': {}}
        pending = []
        for field in ('title', 'abstract'):
            if not row.get(field):
                record.pop(field+'_ja',None)
                continue
            fp = fingerprint(row[field], translator.model)
            cached = old.get('translation', {}).get(field, {})
            if cached.get('hash') == fp and old.get(field+'_ja'):
                record[field+'_ja'] = old[field+'_ja']
                record['translation'][field] = cached
                if force:
                    pending.append((field, fp))
            else:
                # Invalidate stale translations before attempting replacements.
                record.pop(field+'_ja', None)
                pending.append((field, fp))
        record['translation_label'] = 'PLaMo 3 Translate / '+translator.model
        previous[row['id']] = record
        write(output, list(previous.values()))
        if not pending:
            stats['cached'] += 1
            retries.pop(row['id'], None)
            continue
        retry = retries.get(row['id'], {})
        input_hash = hashlib.sha256((row['title']+'\n'+row.get('abstract','')+'|'+translator.model).encode()).hexdigest()
        if not force and retry.get('input_hash') == input_hash and retry.get('next_retry', '') > now.isoformat():
            stats['deferred'] += 1
            continue
        if limit and attempted >= limit:
            continue
        attempted += 1
        try:
            for field, fp in pending:
                stats['requests'] += 1
                record[field+'_ja'] = translator.translate(row[field])
                record['translation'][field] = {
                    'hash': fp, 'model': translator.model, 'date': now.isoformat(), 'format': FORMAT,
                }
                previous[row['id']] = record
                write(output, list(previous.values()))
            retries.pop(row['id'], None)
            stats['translated'] += 1
            print('Translated:', row['id'], flush=True)
            if on_progress:on_progress(record,dict(stats))
        except Exception as exc:
            attempts = retry.get('attempts', 0)+1 if retry.get('input_hash') == input_hash else 1
            minutes = min(15 * 2**min(attempts-1, 7), 24*60)
            retries[row['id']] = {
                'attempts': attempts, 'next_retry': (now+dt.timedelta(minutes=minutes)).isoformat(),
                'input_hash': input_hash, 'error': str(exc),
            }
            stats['failed'] += 1
            print('Translation deferred:', row['id'], str(exc), flush=True)
            if retry_state:
                write(retry_state, retries)
            if not keep_going:
                raise
        finally:
            if retry_state:
                write(retry_state, retries)
    if retry_state:
        write(retry_state, retries)
    return stats

def main():
    p=argparse.ArgumentParser()
    p.add_argument('input');p.add_argument('--output',default='work/translated.json')
    p.add_argument('--base-url',default='http://localhost:1234/v1');p.add_argument('--model')
    p.add_argument('--max-tokens',type=int,default=4096);p.add_argument('--limit',type=int,default=0)
    p.add_argument('--include-pending',action='store_true',help='Translate rights-pending records locally; publication eligibility is unchanged')
    p.add_argument('--force',action='store_true');p.add_argument('--keep-going',action='store_true')
    p.add_argument('--retry-state',default='work/translation-retries.json')
    args=p.parse_args()
    translator=Translator(args.base_url,args.model,args.max_tokens).connect()
    print('Using model:',translator.model,flush=True)
    stats=translate_records(load(args.input,[]),args.output,translator,limit=args.limit,
        force=args.force,keep_going=args.keep_going,retry_state=args.retry_state,include_pending=args.include_pending)
    print(stats)
    return 2 if stats['failed'] else 0

if __name__=='__main__':
    raise SystemExit(main())
