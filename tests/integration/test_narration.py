import hashlib
from fastapi.testclient import TestClient
from sqlalchemy import select
from stock_god.db.models import ListeningProgress
from stock_god.db.session import transaction
from stock_god.learning import narration
from test_workflows import client, post, register


def payload(audio, **changes):
    return {'owner_id': audio['owner_id'], 'locale': audio['locale'], 'version': audio['version'],
            'position_ms': 12000, 'playback_rate': 1.25, 'revision': audio['bookmark']['revision'], **changes}


def test_audio_files_have_integrity_and_all_bilingual_tracks_exist(tmp_path):
    import json
    import runpy
    builder = runpy.run_path(str(narration.ROOT.parents[1] / 'scripts' / 'narration-assets.py'))
    builder['prepare'].__globals__['BUILD'] = tmp_path / 'audio-build'
    builder['prepare']()
    expected = json.loads((tmp_path / 'audio-build' / 'plan.json').read_text(encoding='utf-8'))
    versions = {(track['id'], track['locale']): track['version'] for track in expected}
    tracks = narration.catalog()
    assert len(tracks) == 30
    assert len({(t['id'], t['locale']) for t in tracks}) == 30
    for track in tracks:
        assert track['version'] == versions[(track['id'], track['locale'])], 'Narration must be rebuilt after its text changes.'
        data = (narration.ROOT / track['file']).read_bytes()
        assert data.startswith(b'ID3') and len(data) > 10000
        assert hashlib.sha256(data).hexdigest() == track['sha256']
        assert track['duration_ms'] > 3000
        assert track['sections'][0]['start_ms'] == 0
        assert all(0 <= section['start_ms'] < track['duration_ms'] for section in track['sections'])


def test_audio_is_authenticated_seekable_and_respects_course_locks(client):
    audio = client.get('/api/courses/account').json()['narration']
    full = client.get(audio['url'])
    assert full.status_code == 200 and full.headers['content-type'] == 'audio/mpeg'
    partial = client.get(audio['url'], headers={'Range': 'bytes=0-127'})
    assert partial.status_code == 206
    assert partial.content == full.content[:128]
    assert partial.headers['content-range'].startswith('bytes 0-127/')
    with TestClient(client.app) as guest:
        assert guest.get(audio['url']).status_code == 401
    locked = narration.track_for('lesson-orders', 'en')
    assert client.get(f"/api/narration/lesson-orders/en/{locked['version']}.mp3").status_code == 409
    assert client.get('/api/courses/orders/narration?locale=en').status_code == 409
    assert client.get(audio['url'].replace(audio['version'], 'obsolete')).status_code == 404
    english = client.get('/api/courses/account/narration?locale=en').json()
    assert english['locale'] == 'en' and english['url'] != audio['url']
    assert client.get(english['url'], headers={'Accept-Language': 'zh-CN'}).headers['content-language'] == 'en'
    coach = post(client, '/coach', {'question': 'Why did it not fill?', 'lesson_id': 'account'}).json()
    assert coach['narration']['id'] == 'coach-orders'
    assert client.get(coach['narration']['url']).status_code == 200


def test_listening_bookmarks_are_owned_versioned_and_never_award_xp(client):
    audio = client.get('/api/courses/account').json()['narration']
    first = post(client, '/courses/account/listening', payload(audio), key='narration-intent-1')
    assert first.status_code == 200, first.text
    assert first.json() == {'position_ms': 12000, 'playback_rate': 1.25, 'revision': 1}
    assert post(client, '/courses/account/listening', payload(audio), key='narration-intent-1').json() == first.json()
    assert post(client, '/courses/account/listening', payload(audio, position_ms=5000)).status_code == 409
    assert post(client, '/courses/account/listening', payload(audio, revision=1, position_ms=5000)).status_code == 200
    assert client.get('/api/courses/account').json()['narration']['bookmark']['position_ms'] == 5000
    english = client.get('/api/courses/account/narration?locale=en').json()
    assert english['bookmark']['position_ms'] == 0
    assert post(client, '/courses/account/listening', payload(english, position_ms=english['duration_ms'])).status_code == 200
    state = client.get('/api/state').json()
    assert state['player']['xp'] == 0 and not state['courses'][0]['completed']
    assert state['courses'][1]['locked']
    assert len(client.get('/api/listening').json()) == 2
    assert len(client.get('/api/export').json()['tables']['listening_progress']) == 2
    with TestClient(client.app) as other:
        register(other, 'other_listener')
        assert other.get('/api/listening').json() == []
        assert post(other, '/courses/account/listening', payload(audio)).status_code == 403
    post(client, '/auth/logout')
    post(client, '/auth/login', {'username': 'testlearner', 'password': 'a-test-password-123'})
    assert client.get('/api/courses/account').json()['narration']['bookmark']['position_ms'] == 5000


def test_bookmark_validation_and_audio_revision_reset(client):
    audio = client.get('/api/courses/account').json()['narration']
    for changes in [{'position_ms': -1}, {'position_ms': True}, {'position_ms': audio['duration_ms'] + 1}, {'playback_rate': 100}, {'locale': 'fr'}]:
        assert post(client, '/courses/account/listening', payload(audio, **changes)).status_code == 422
    assert post(client, '/courses/account/listening', payload(audio, version='obsolete-version-0000')).status_code == 409
    assert post(client, '/courses/account/listening', payload(audio)).status_code == 200
    with transaction(client.app.state.factory) as s:
        row = s.scalar(select(ListeningProgress))
        row.audio_version = 'earlier-audio'
    refreshed = client.get('/api/courses/account').json()['narration']['bookmark']
    assert refreshed['position_ms'] == 0 and refreshed['revision'] == 1
