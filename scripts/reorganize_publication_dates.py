"""One-time reorganization of the initial bulk import by publication week."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

from common import ROOT, load, write
import auto

JST = dt.timezone(dt.timedelta(hours=9))


def read_js(path):
    text = path.read_text(encoding='utf-8')
    return json.loads(text.split('=', 1)[1].strip().rstrip(';'))


def week_key(value):
    day = dt.date.fromisoformat(str(value)[:10])
    iso = day.isocalendar()
    return f'{iso.year}-W{iso.week:02d}'


def monday_for(issue_id):
    year, week = issue_id.split('-W')
    return dt.date.fromisocalendar(int(year), int(week), 1)


def entry_for(issue_id, data, path, updated):
    monday = monday_for(issue_id)
    end = dt.datetime.combine(monday + dt.timedelta(days=7), dt.time(), JST)
    latest = max(dt.date.fromisoformat(str(p['date'])[:10]) for p in data['papers'])
    return {
        'id': issue_id,
        'date': monday.isoformat(),
        'year': monday.year,
        'month': monday.month,
        'path': 'data/issues/' + path.name,
        'count': len(data['papers']),
        'week_ends_at': end.isoformat(),
        'archive_available_at': dt.datetime.combine(latest + dt.timedelta(days=7), dt.time(), JST).isoformat(),
        'updated_at': updated.isoformat(),
        'doi_keys': sorted({key for paper in data['papers'] for key in auto.paper_keys(paper)}),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--today', help='JST date for the seven-day recent window (YYYY-MM-DD)')
    parser.add_argument('--active-updated-at', help='keep the active issue eligible for today\'s scheduled update')
    parser.add_argument('--write', action='store_true', help='write the reorganization (required)')
    args = parser.parse_args()
    if not args.write:
        parser.error('pass --write to modify the published issue data')

    today = dt.date.fromisoformat(args.today) if args.today else dt.datetime.now(JST).date()
    recent_since = today - dt.timedelta(days=6)
    index_path = ROOT / 'docs/data/archive-index.json'
    old_index = load(index_path, {'schema_version': 1, 'issues': []})
    old_front = read_js(ROOT / 'docs/data/papers.js')
    collected = list(old_front.get('papers', []))
    choice_context = old_front.get('choice_context')
    # Include previously archived payloads so the maintenance command is repeatable.
    for entry in old_index.get('issues', []):
        issue_path = ROOT / 'docs' / entry['path']
        if not issue_path.exists():
            continue
        prior = load(issue_path, {})
        collected.extend(prior.get('papers', []))
        choice_context = choice_context or prior.get('choice_context')
    papers = list({paper.get('id'): paper for paper in collected if paper.get('id')}.values())
    groups = {}
    for paper in papers:
        groups.setdefault(week_key(paper['date']), []).append(paper)

    now = dt.datetime.now(JST)
    issue_template = old_front.get('issue', {})
    entries = []
    for issue_id, rows in sorted(groups.items()):
        rows.sort(key=lambda paper: (str(paper.get('date', '')), str(paper.get('id', ''))))
        monday = monday_for(issue_id)
        data = {
            **old_front,
            'issue': {
                **issue_template,
                'id': issue_id,
                'label': issue_id,
                'date': monday.isoformat(),
                'publication_mode': 'daily',
                'week_ends_at': dt.datetime.combine(monday + dt.timedelta(days=7), dt.time(), JST).isoformat(),
                'archive_available_at': dt.datetime.combine(max(dt.date.fromisoformat(str(p['date'])[:10]) for p in rows) + dt.timedelta(days=7), dt.time(), JST).isoformat(),
                'updated_at': now.isoformat(),
                **({'daily_updated_at': args.active_updated_at or issue_template.get('daily_updated_at') or issue_template.get('updated_at', now.isoformat())} if issue_id == week_key(today.isoformat()) else {}),
                'added_ids': [],
                'added_date': today.isoformat(),
            },
            'papers': rows,
        }
        if choice_context:
            data['choice_context'] = {
                'catalog': choice_context.get('catalog', []),
                'papers': [{key: paper[key] for key in ('answer_journal', 'options') if key in paper} for paper in rows],
            }
        filename = issue_id + '.json'
        path = ROOT / 'docs/data/issues' / filename
        write(path, data)
        entries.append(entry_for(issue_id, data, path, now))

    active_id = week_key(today.isoformat())
    if active_id not in groups:
        raise RuntimeError(f'No papers for the current ISO week {active_id}; refusing an empty front page')
    current = load(ROOT / 'docs/data/issues' / (active_id + '.json'))
    front = ROOT / 'docs/data/papers.js'
    front.write_text('window.PAPER_DATA = ' + json.dumps(current, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8')
    recent = [p for p in papers if dt.date.fromisoformat(str(p['date'])[:10]) >= recent_since]
    recent.sort(key=lambda p: (str(p.get('date', '')), str(p.get('id', ''))), reverse=True)
    (ROOT / 'docs/data/recent-papers.js').write_text(
        'window.PAPER_RECENT_DATA = ' + json.dumps(recent, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8')
    write(index_path, {
        'schema_version': 1,
        'archive_after_days': 0,
        'archive_policy': 'weekly',
        'issues': entries,
    })
    print(f'Organized {len(papers)} papers into {len(entries)} publication weeks; '
          f'{len(recent)} papers dated {recent_since.isoformat()} or later are in the recent list.')


if __name__ == '__main__':
    main()
