"""Real local HTTP + original worker; template fallback, no LLM or Telegram calls."""
import asyncio
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
(ROOT / 'data').mkdir(exist_ok=True)
# Explicitly override inherited credentials: this test must stay offline.
os.environ.update(OPENAI_API_KEY='', TELEGRAM_BOT_TOKEN='', TELEGRAM_USER_CHAT_ID='',
                  TELEGRAM_CHAT_ID='', TARGET_SITE_URL='http://127.0.0.1:18009',
                  WORKER_API_TOKEN='local-demo-only-not-a-secret',
                  LOCAL_DATABASE_URL='sqlite+aiosqlite:///data/reviews.sqlite3',
                  STATE_FILE_PATH='data/state.json')
import httpx

async def check():
    sys.path.insert(0, str(ROOT / 'worker'))
    import worker
    from state import WorkerState
    cases = [
        ('Анна', 'Отлично, спасибо! Товар понравился, доставка быстро.', 'positive'),
        ('Иван', 'Ужас, товар не работает, я недоволен.', 'negative'),
        ('Ольга', 'Заказ получен во вторник. Упаковка серая.', 'neutral'),
    ]
    async with httpx.AsyncClient(base_url='http://127.0.0.1:18009') as client:
        ids = []
        for name, text, tone in cases:
            r = await client.post('/api/reviews', json={'name': name, 'text': text})
            assert r.status_code == 201, r.text
            ids.append(r.json()['id'])
        await worker.wait_for_site()
        await worker.process_new_reviews()
        before = (await client.get('/api/reviews')).json()
        worker.state = WorkerState('data/state.json')  # emulate state reload on restart
        await worker.process_new_reviews()
        after = (await client.get('/api/reviews')).json()
        assert before == after, 'Duplicate or modified response on repeated run'
        rows = []
        for review_id, (name, text, expected) in zip(ids, cases):
            review = next(x for x in after if x['id'] == review_id)
            replies = [x for x in after if x['parent_id'] == review_id]
            assert review['tone'] == expected
            assert review['status'] == 'processed'
            assert len(replies) == 1 and replies[0]['status'] == 'processed'
            assert replies[0]['text'].strip()
            assert worker.state.is_processed(review_id)
            rows.append({'id': review_id, 'review': text, 'expected': expected,
                         'actual': review['tone'], 'status': review['status'],
                         'reply': replies[0]['text'], 'reply_count': len(replies),
                         'mode': 'LOCAL_TEMPLATE_MOCK_NO_LLM', 'result': 'PASS'})
        # Check state guard separately: re-expose an already processed review as new.
        r = await client.patch(f'/api/reviews/{ids[0]}', headers=worker.client._headers,
                               json={'status': 'new'})
        r.raise_for_status()
        await worker.process_new_reviews()
        guarded = (await client.get('/api/reviews')).json()
        assert len(guarded) == len(after), 'State guard failed'
        r = await client.patch(f'/api/reviews/{ids[0]}', headers=worker.client._headers,
                               json={'status': 'processed'})
        r.raise_for_status()
        final = (await client.get('/api/reviews')).json()
        (ROOT/'reviews_snapshot.json').write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding='utf-8')
        (ROOT/'test_results.json').write_text(json.dumps({'mode':'LOCAL_TEMPLATE_MOCK_NO_LLM',
            'telegram':'disabled; not tested', 'repeat_poll':'PASS', 'state_reload':'PASS',
            'state_guard':'PASS', 'cases':rows}, ensure_ascii=False, indent=2), encoding='utf-8')
        with (ROOT/'Таблица_тестирования.csv').open('w', encoding='utf-8-sig', newline='') as f:
            writer=csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
        print('PASS: 3 tones, 3 replies, processed statuses, repeat poll, state reload and state guard. MOCK; NO LLM.')

if __name__ == '__main__':
    with (ROOT/'server.log').open('w', encoding='utf-8') as log:
        server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '18009'], stdout=log, stderr=log)
        try:
            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError('Server exited; see server.log')
                try:
                    if httpx.get('http://127.0.0.1:18009/', timeout=1).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(.1)
            else:
                raise RuntimeError('Server startup timeout')
            asyncio.run(check())
        finally:
            server.terminate()
            server.wait(timeout=10)
