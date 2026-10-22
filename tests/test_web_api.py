from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


def test_health_and_summary_serve_pipeline_results():
    health = client.get('/api/health')
    summary = client.get('/api/summary')

    assert health.status_code == 200
    assert health.json()['status'] == 'ok'
    assert health.json()['analysis_status'] == 'ready'
    assert summary.status_code == 200
    assert summary.json()['status'] == 'ready'
    assert summary.json()['users_analyzed'] == 5000
    assert summary.json()['cancellations'] + summary.json()['not_cancelled'] == 5000


def test_filters_update_segment_count_and_include_valid_groups():
    filters = client.get('/api/filters').json()
    assert filters['status'] == 'ready'
    assert filters['countries']

    all_users = client.get('/api/segments').json()
    per_country = client.get('/api/segments', params={'country': filters['countries'][0]}).json()

    assert all_users['status'] == 'ready'
    assert per_country['status'] == 'ready'
    assert per_country['users'] <= all_users['users']
    assert per_country['filters']['country'] == filters['countries'][0]
    assert set(per_country['groups']) == {'plan', 'country', 'payment_method', 'device'}


def test_models_and_quality_responses_have_real_metrics_and_audit():
    models = client.get('/api/models').json()
    quality = client.get('/api/quality').json()

    assert models['status'] == 'ready'
    assert {'LogisticRegression', 'RandomForestClassifier'} <= {item['modelo'] for item in models['metrics']}
    assert models['positive_class'] == 1
    assert quality['original_rows'] == 5025
    assert quality['final_rows'] == 5000
    assert quality['exact_duplicates'] == 25
    assert quality['issue_incidences'] >= quality['exact_duplicates']


def test_prediction_uses_persisted_pipeline_and_rejects_invalid_fields():
    models = client.get('/api/models').json()
    assert models['model_available'] is True
    features = {}
    for field in models['input_schema']:
        if field['kind'] == 'number':
            features[field['name']] = field['minimum']
        else:
            features[field['name']] = field['options'][0] if field['options'] else 'categoría nueva'

    response = client.post('/api/predict', json={'features': features})
    assert response.status_code == 200
    result = response.json()
    assert result['predicted_class'] in (0, 1)
    assert result['threshold'] == 0.5
    assert result['model_version']
    assert 'cancelo' not in features

    invalid = client.post('/api/predict', json={'features': {'cancelo': 1}})
    assert invalid.status_code == 422


def test_downloads_allow_only_named_results():
    listed = client.get('/api/downloads').json()
    assert listed['status'] == 'ready'
    assert any(item['id'] == 'presentation' and item['available'] for item in listed['items'])
    assert client.get('/api/downloads/unknown').status_code == 404
