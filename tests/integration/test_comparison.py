from fastapi.testclient import TestClient
from stock_god.db.models import Job
from stock_god.db.session import transaction
from stock_god.jobs.worker import run_once
from test_workflows import client, post, register


def create(client, long):
    response = post(client, '/experiments', {'short_window': 3, 'long_window': long, 'allocation': 30})
    assert response.status_code == 200
    assert run_once(client.app.state.factory)
    return response.json()['id']


def comparison(client, ids):
    return client.get('/api/experiments/comparison', params=[('ids', identifier) for identifier in ids])


def test_comparison_aligns_common_closes_without_changing_reports(client):
    a, b = create(client, 10), create(client, 20)
    originals = client.get('/api/experiments').json()
    result = comparison(client, [a, b])
    assert result.status_code == 200, result.text
    report = result.json()
    assert report['start_day'] == 20 and report['end_day'] == 59
    assert [r['id'] for r in report['rows']] == [a, b]
    assert all(r['curve'][0]['value'] == '100.00' and len(r['curve']) == 40 for r in report['rows'])
    assert client.get('/api/experiments').json() == originals
    english = client.get('/api/experiments/comparison', params=[('ids', a), ('ids', b)], headers={'Accept-Language': 'en'}).json()
    assert english['rows'] == report['rows']
    assert all(not any('\u4e00' <= c <= '\u9fff' for c in note) for note in english['notes'])


def test_comparison_rejects_incompatible_and_unowned_experiments(client):
    a, b = create(client, 10), create(client, 20)
    assert comparison(client, [a, a]).status_code == 422
    assert comparison(client, [a, 'missing']).status_code == 404
    with TestClient(client.app) as other:
        register(other, 'comparison_other')
        assert comparison(other, [a, b]).status_code == 404
    with transaction(client.app.state.factory) as s:
        job = s.get(Job, b)
        job.result = {**job.result, 'data_version': 'another-data-version'}
    assert comparison(client, [a, b]).status_code == 409
