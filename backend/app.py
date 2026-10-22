from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / 'data' / 'raw' / 'neflix.csv'
CLEAN_CSV = ROOT / 'data' / 'processed' / 'netflix_limpio.csv'
AUDIT_CSV = ROOT / 'data' / 'processed' / 'auditoria_limpieza_netflix.csv'
METRICS_CSV = ROOT / 'reports' / 'metrics' / 'metricas_modelos.csv'
EVALUATION_JSON = ROOT / 'reports' / 'metrics' / 'evaluation_netflix.json'
RUN_JSON = ROOT / 'reports' / 'metrics' / 'analysis_run.json'
MODEL_PATH = ROOT / 'reports' / 'models' / 'netflix_churn_pipeline.joblib'

DOWNLOADS: dict[str, tuple[Path, str, str]] = {
    'clean-dataset': (CLEAN_CSV, 'netflix_limpio.csv', 'text/csv'),
    'metrics': (METRICS_CSV, 'metricas_modelos.csv', 'text/csv'),
    'evaluation': (EVALUATION_JSON, 'evaluation_netflix.json', 'application/json'),
    'analysis-run': (RUN_JSON, 'analysis_run.json', 'application/json'),
    'presentation': (
        ROOT / 'reports' / 'presentacion_netflix.pptx',
        'presentacion_netflix.pptx',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    ),
    'importance': (
        ROOT / 'reports' / 'metrics' / 'variables_importantes.csv',
        'variables_importantes.csv',
        'text/csv',
    ),
    'audit': (AUDIT_CSV, 'auditoria_limpieza_netflix.csv', 'text/csv'),
}

app = FastAPI(
    title='Netflix Churn Analytics API',
    version='1.0.0',
    description='API local para consultar resultados calculados del caso académico de cancelaciones.',
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://127.0.0.1:5173', 'http://localhost:5173'],
    allow_credentials=False,
    allow_methods=['GET', 'POST'],
    allow_headers=['Content-Type'],
)


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    features: dict[str, Any]


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, bool):
        return value
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        with path.open(encoding='utf-8') as file:
            result = json.load(file, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(f'Invalid JSON number: {token}')))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f'No se pudo leer el artefacto {path.name}: {exc}') from exc
    if not isinstance(result, dict):
        raise HTTPException(status_code=500, detail=f'El artefacto {path.name} debe contener un objeto JSON.')
    return json_safe(result)


def read_clean() -> pd.DataFrame | None:
    if not CLEAN_CSV.is_file():
        return None
    try:
        return pd.read_csv(CLEAN_CSV)
    except (OSError, pd.errors.ParserError, UnicodeError) as exc:
        raise HTTPException(status_code=500, detail=f'No se pudo leer el dataset limpio: {exc}') from exc


def pending(message: str) -> dict[str, Any]:
    return {'status': 'pending', 'message': message}


def display_category(series: pd.Series) -> pd.Series:
    return series.fillna('Sin dato').astype(str)


def group_rates(frame: pd.DataFrame, column: str) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    working = frame.assign(_grupo=display_category(frame[column]))
    grouped = working.groupby('_grupo', dropna=False)['cancelo'].agg(users='count', cancellations='sum').reset_index()
    grouped['rate'] = grouped['cancellations'] / grouped['users']
    grouped = grouped.sort_values(['rate', 'users'], ascending=[False, False])
    return json_safe([
        {
            'group': row['_grupo'],
            'users': int(row['users']),
            'cancellations': int(row['cancellations']),
            'rate': float(row['rate']),
        }
        for _, row in grouped.iterrows()
    ])


def filtered_frame(df: pd.DataFrame, country: str | None, plan: str | None, device: str | None) -> pd.DataFrame:
    result = df.loc[df['cancelo'].notna()].copy()
    for column, value in (
        ('pais', country),
        ('plan', plan),
        ('dispositivo_principal', device),
    ):
        if value:
            result = result.loc[display_category(result[column]).eq(value)]
    return result


@app.get('/api/health')
def health() -> dict[str, Any]:
    run = read_json(RUN_JSON)
    clean_exists = CLEAN_CSV.is_file()
    metrics_exists = METRICS_CSV.is_file() and EVALUATION_JSON.is_file()
    return {
        'status': 'ok',
        'application': 'Netflix Churn Analytics',
        'analysis_status': 'ready' if clean_exists and metrics_exists else 'pending',
        'model_available': MODEL_PATH.is_file(),
        'generated_at_utc': run.get('generated_at_utc') if run else None,
        'source': run.get('source') if run else 'data/raw/neflix.csv',
        'model_version': run.get('model_version') if run else None,
    }


@app.get('/api/summary')
def summary() -> dict[str, Any]:
    df = read_clean()
    run = read_json(RUN_JSON)
    if df is None or 'cancelo' not in df:
        return pending('Análisis pendiente. Desde la raíz, ejecuta: npm run analysis')
    target = pd.to_numeric(df['cancelo'], errors='coerce').dropna()
    if target.empty:
        return pending('No hay etiquetas de cancelación válidas en el dataset limpio.')
    valid = df.loc[pd.to_numeric(df['cancelo'], errors='coerce').notna()].copy()
    valid['cancelo'] = pd.to_numeric(valid['cancelo']).astype(int)
    findings: list[dict[str, Any]] = []
    for column, label in (
        ('plan', 'Plan'),
        ('pais', 'País'),
        ('metodo_pago', 'Método de pago'),
        ('dispositivo_principal', 'Dispositivo'),
    ):
        rates = group_rates(valid, column)
        if rates:
            leader = rates[0]
            findings.append({
                'label': label,
                'group': leader['group'],
                'rate': leader['rate'],
                'users': leader['users'],
                'cancellations': leader['cancellations'],
            })
    return json_safe({
        'status': 'ready',
        'source': 'data/raw/neflix.csv',
        'updated_at': run.get('generated_at_utc') if run else None,
        'model_version': run.get('model_version') if run else None,
        'users_analyzed': int(target.size),
        'cancellations': int((target == 1).sum()),
        'not_cancelled': int((target == 0).sum()),
        'cancellation_rate': float((target == 1).mean()),
        'findings': findings,
    })


@app.get('/api/quality')
def quality() -> dict[str, Any]:
    if not RAW_CSV.is_file():
        return pending('No se encuentra data/raw/neflix.csv.')
    if not CLEAN_CSV.is_file():
        return pending('Análisis pendiente. Desde la raíz, ejecuta: npm run analysis')
    try:
        raw = pd.read_csv(RAW_CSV)
        clean = pd.read_csv(CLEAN_CSV)
        audit = pd.read_csv(AUDIT_CSV) if AUDIT_CSV.is_file() else pd.DataFrame()
    except (OSError, pd.errors.ParserError, UnicodeError) as exc:
        raise HTTPException(status_code=500, detail=f'Error leyendo los archivos de calidad: {exc}') from exc

    nulls = [
        {'variable': str(column), 'count': int(count), 'percent': float(count / len(clean)) if len(clean) else 0}
        for column, count in clean.isna().sum().items()
        if count
    ]
    audit_rows = audit.fillna('').to_dict(orient='records') if not audit.empty else []
    issue_incidences = (
        int(pd.to_numeric(audit.get('cantidad_registros_afectados', pd.Series(dtype=float)), errors='coerce').fillna(0).sum())
        if not audit.empty else 0
    )
    return json_safe({
        'status': 'ready',
        'original_rows': int(len(raw)),
        'final_rows': int(len(clean)),
        'exact_duplicates': int(raw.duplicated().sum()),
        'repeated_user_rows': int(raw['id_usuario'].duplicated().sum()) if 'id_usuario' in raw else 0,
        'remaining_duplicate_rows': int(clean.duplicated().sum()),
        'unique_users': int(clean['id_usuario'].nunique()) if 'id_usuario' in clean else None,
        'nulls_by_variable': nulls,
        'audit_decisions': audit_rows,
        'issue_incidences': issue_incidences,
        'records_removed_or_merged': int(len(raw) - len(clean)),
        'counts_note': 'Las incidencias suman conteos por regla/variable y pueden incluir una misma fila más de una vez. Los registros retirados/agrupados son la diferencia de filas del dataset.',
    })


@app.get('/api/segments')
def segments(
    country: str | None = Query(default=None, max_length=80),
    plan: str | None = Query(default=None, max_length=40),
    device: str | None = Query(default=None, max_length=80),
) -> dict[str, Any]:
    df = read_clean()
    if df is None:
        return pending('Análisis pendiente. Desde la raíz, ejecuta: npm run analysis')
    frame = filtered_frame(df, country, plan, device)
    if frame.empty:
        return {'status': 'empty', 'message': 'No hay usuarios para esta combinación de filtros.', 'users': 0, 'cancellations': 0, 'not_cancelled': 0, 'cancellation_rate': None, 'groups': {}, 'behavior': []}
    target = pd.to_numeric(frame['cancelo'], errors='coerce')
    frame = frame.loc[target.notna()].copy()
    frame['cancelo'] = pd.to_numeric(frame['cancelo']).astype(int)
    if frame.empty:
        return {'status': 'empty', 'message': 'No hay etiquetas válidas para la combinación seleccionada.', 'users': 0, 'cancellations': 0, 'not_cancelled': 0, 'cancellation_rate': None, 'groups': {}, 'behavior': []}

    behavior: list[dict[str, Any]] = []
    for column, label, unit in (
        ('horas_vistas_mes', 'Horas vistas al mes', 'horas'),
        ('dias_desde_ultimo_acceso', 'Días desde último acceso', 'días'),
        ('calificacion_promedio', 'Calificación promedio', 'puntos (1–5)'),
        ('tickets_soporte', 'Tickets de soporte', 'tickets'),
    ):
        valid = frame[[column, 'cancelo']].copy()
        valid[column] = pd.to_numeric(valid[column], errors='coerce')
        valid = valid.dropna(subset=[column])
        groups = []
        for label_value, class_value in (('No cancela', 0), ('Sí cancela', 1)):
            values = valid.loc[valid['cancelo'] == class_value, column]
            groups.append({
                'state': label_value,
                'users': int(len(values)),
                'median': float(values.median()) if len(values) else None,
                'q1': float(values.quantile(0.25)) if len(values) else None,
                'q3': float(values.quantile(0.75)) if len(values) else None,
            })
        behavior.append({'variable': column, 'label': label, 'unit': unit, 'groups': groups})

    return json_safe({
        'status': 'ready',
        'filters': {'country': country, 'plan': plan, 'device': device},
        'users': int(len(frame)),
        'cancellations': int(frame['cancelo'].sum()),
        'not_cancelled': int((frame['cancelo'] == 0).sum()),
        'cancellation_rate': float(frame['cancelo'].mean()),
        'groups': {
            'plan': group_rates(frame, 'plan'),
            'country': group_rates(frame, 'pais'),
            'payment_method': group_rates(frame, 'metodo_pago'),
            'device': group_rates(frame, 'dispositivo_principal'),
        },
        'behavior': behavior,
    })


@app.get('/api/filters')
def filters() -> dict[str, Any]:
    df = read_clean()
    if df is None:
        return pending('Análisis pendiente. Desde la raíz, ejecuta: npm run analysis')
    return json_safe({
        'status': 'ready',
        'countries': sorted(display_category(df['pais']).unique().tolist()),
        'plans': sorted(display_category(df['plan']).unique().tolist()),
        'devices': sorted(display_category(df['dispositivo_principal']).unique().tolist()),
    })


@app.get('/api/models')
def models() -> dict[str, Any]:
    evaluation = read_json(EVALUATION_JSON)
    if evaluation is None or not METRICS_CSV.is_file():
        return pending('Evaluación pendiente. Desde la raíz, ejecuta: npm run analysis')
    try:
        metrics = pd.read_csv(METRICS_CSV).replace({np.nan: None}).to_dict(orient='records')
    except (OSError, pd.errors.ParserError, UnicodeError) as exc:
        raise HTTPException(status_code=500, detail=f'No se pudo leer la comparación de modelos: {exc}') from exc
    reports = {}
    for name in ('DummyClassifier', 'LogisticRegression', 'RandomForestClassifier'):
        report_path = ROOT / 'reports' / 'metrics' / f'{name.lower()}_report.json'
        report = read_json(report_path)
        if report is not None:
            reports[name] = report
    return json_safe({
        'status': 'ready',
        'source': evaluation.get('source'),
        'updated_at': evaluation.get('generated_at_utc'),
        'model_version': evaluation.get('model_version'),
        'model_available': MODEL_PATH.is_file(),
        'input_schema': evaluation.get('input_schema', []),
        'threshold': evaluation.get('threshold', 0.5),
        'positive_class': evaluation.get('positive_class', 1),
        'split': evaluation.get('split'),
        'test_rows': evaluation.get('test_rows'),
        'test_class_counts': evaluation.get('test_class_counts'),
        'metrics': metrics,
        'reports': reports,
        'temporal_limitation': evaluation.get('temporal_limitation'),
    })


@app.get('/api/factors')
def factors() -> dict[str, Any]:
    evaluation = read_json(EVALUATION_JSON)
    path = ROOT / 'reports' / 'metrics' / 'variables_importantes.csv'
    if evaluation is None or not path.is_file():
        return pending('Importancia de variables pendiente. Desde la raíz, ejecuta: npm run analysis')
    try:
        values = pd.read_csv(path).to_dict(orient='records')
    except (OSError, pd.errors.ParserError, UnicodeError) as exc:
        raise HTTPException(status_code=500, detail=f'No se pudo leer la importancia de variables: {exc}') from exc
    return json_safe({
        'status': 'ready',
        'model_version': evaluation.get('model_version'),
        'selected_model': evaluation.get('selected_for_permutation_importance'),
        'method': evaluation.get('permutation_importance'),
        'causality_note': 'La importancia predictiva indica asociación con el desempeño del modelo; no demuestra causalidad.',
        'items': values,
    })


@app.post('/api/predict')
def predict(request: PredictionRequest) -> dict[str, Any]:
    if not MODEL_PATH.is_file():
        raise HTTPException(status_code=409, detail='Predicción no disponible: falta el pipeline entrenado. Ejecuta npm run analysis.')
    evaluation = read_json(EVALUATION_JSON)
    if evaluation is None:
        raise HTTPException(status_code=409, detail='Predicción no disponible: falta el artefacto de evaluación del modelo.')
    schema = evaluation.get('input_schema', [])
    expected = {item.get('name'): item for item in schema if isinstance(item, dict) and item.get('name')}
    supplied = request.features
    missing = sorted(set(expected) - set(supplied))
    unknown = sorted(set(supplied) - set(expected))
    if missing or unknown:
        raise HTTPException(status_code=422, detail={'message': 'Las variables no coinciden con el pipeline entrenado.', 'missing': missing, 'unknown': unknown})

    row: dict[str, Any] = {}
    for name, definition in expected.items():
        value = supplied[name]
        if value is None:
            row[name] = np.nan
            continue
        if definition.get('kind') == 'number':
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise HTTPException(status_code=422, detail=f'{name} debe ser numérico o nulo.')
            if not math.isfinite(float(value)):
                raise HTTPException(status_code=422, detail=f'{name} debe ser un número finito.')
            row[name] = float(value)
        else:
            if not isinstance(value, str) or not value.strip():
                raise HTTPException(status_code=422, detail=f'{name} debe ser texto no vacío o nulo.')
            row[name] = value.strip()

    try:
        pipeline = joblib.load(MODEL_PATH)
        data = pd.DataFrame([row], columns=list(expected))
        predicted_class = int(pipeline.predict(data)[0])
        probabilities: dict[str, float] = {}
        if hasattr(pipeline, 'predict_proba'):
            values = pipeline.predict_proba(data)[0]
            probabilities = {str(int(label)): float(score) for label, score in zip(pipeline.classes_, values)}
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
        raise HTTPException(status_code=500, detail=f'No se pudo ejecutar el pipeline guardado: {exc}') from exc
    threshold = float(evaluation.get('threshold', 0.5))
    return json_safe({
        'status': 'ready',
        'predicted_class': predicted_class,
        'label': 'Sí cancela' if predicted_class == 1 else 'No cancela',
        'probability_estimate': probabilities.get('1'),
        'class_scores': probabilities,
        'threshold': threshold,
        'model_version': evaluation.get('model_version'),
        'calibration_note': 'La puntuación de LogisticRegression no está calibrada y no es una certeza individual.',
        'academic_note': evaluation.get('temporal_limitation'),
    })


@app.get('/api/downloads')
def list_downloads() -> dict[str, Any]:
    return {
        'status': 'ready',
        'items': [
            {'id': download_id, 'filename': filename, 'available': path.is_file()}
            for download_id, (path, filename, _media_type) in DOWNLOADS.items()
        ],
    }


@app.get('/api/downloads/{download_id}')
def download(download_id: str) -> FileResponse:
    item = DOWNLOADS.get(download_id)
    if item is None:
        raise HTTPException(status_code=404, detail='El archivo solicitado no está autorizado para descarga.')
    path, filename, media_type = item
    if not path.is_file():
        raise HTTPException(status_code=404, detail='El archivo autorizado aún no está generado.')
    return FileResponse(path=path, filename=filename, media_type=media_type)
