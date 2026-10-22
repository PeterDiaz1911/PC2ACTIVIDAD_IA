from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.limpieza import cargar_y_limpiar, exportar_datos_limpios
from src.modelado import MODEL_VERSION, entrenar_modelos
from src.presentacion import build_presentation
from src.visualizacion import generar_graficos_exploratorios

ROOT = Path(__file__).resolve().parents[1]


def ejecutar_analisis() -> dict:
    raw_path = ROOT / 'data' / 'raw' / 'neflix.csv'
    if not raw_path.is_file():
        raise FileNotFoundError(f'No se encontró el CSV original: {raw_path}')

    raw_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    raw = pd.read_csv(raw_path)
    cleaned, audit = cargar_y_limpiar(raw_path)
    clean_path = ROOT / 'data' / 'processed' / 'netflix_limpio.csv'
    exportar_datos_limpios(cleaned, audit, clean_path)

    figure_paths = generar_graficos_exploratorios(
        cleaned.loc[cleaned['cancelo'].notna()],
        ROOT / 'reports' / 'figures',
    )
    metrics, importance = entrenar_modelos(cleaned)
    presentation = build_presentation()

    run = {
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'source': 'data/raw/neflix.csv',
        'source_sha256': raw_hash,
        'original_rows': int(len(raw)),
        'clean_rows': int(len(cleaned)),
        'target_valid_rows': int(cleaned['cancelo'].notna().sum()),
        'model_version': MODEL_VERSION,
        'model_artifact': 'reports/models/netflix_churn_pipeline.joblib',
        'metrics_file': 'reports/metrics/metricas_modelos.csv',
        'figures': [path.relative_to(ROOT).as_posix() for path in figure_paths],
        'presentation': presentation.relative_to(ROOT).as_posix(),
        'best_test_f1': float(metrics.loc[metrics['modelo'].eq('LogisticRegression'), 'f1'].iloc[0]),
        'top_predictive_features': importance['variable'].head(5).tolist(),
    }
    run_path = ROOT / 'reports' / 'metrics' / 'analysis_run.json'
    run_path.write_text(json.dumps(run, ensure_ascii=False, allow_nan=False, indent=2), encoding='utf-8')
    return run


def main() -> None:
    result = ejecutar_analisis()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
