from pathlib import Path

import pandas as pd

from src.limpieza import cargar_y_limpiar
from src.modelado import preparar_dataset

ROOT = Path(__file__).resolve().parents[1]


def test_original_dataset_shape_and_duplicate_counts():
    raw = pd.read_csv(ROOT / 'data' / 'raw' / 'neflix.csv')

    assert raw.shape == (5025, 20)
    assert raw.duplicated().sum() == 25
    assert raw['id_usuario'].duplicated().sum() == 25


def test_cleaning_preserves_target_and_resolves_duplicate_users():
    cleaned, audit = cargar_y_limpiar(ROOT / 'data' / 'raw' / 'neflix.csv')

    assert len(cleaned) == 5000
    assert cleaned['id_usuario'].is_unique
    assert not cleaned.duplicated().any()
    assert set(cleaned['cancelo'].dropna().unique()) == {0, 1}
    assert cleaned['cancelo'].isna().sum() == 0
    assert cleaned['metodo_pago'].isna().sum() == 100
    assert 'problema' in audit.columns


def test_model_split_excludes_identifiers_and_registration_date():
    cleaned, _ = cargar_y_limpiar(ROOT / 'data' / 'raw' / 'neflix.csv')
    X_train, y_train, X_test, y_test = preparar_dataset(cleaned)

    assert len(X_train) + len(X_test) == len(cleaned)
    assert len(X_train) == 3750
    assert len(X_test) == 1250
    assert 'id_usuario' not in X_train.columns
    assert 'fecha_registro' not in X_train.columns
    assert y_train.value_counts(normalize=True).round(2).to_dict() == y_test.value_counts(normalize=True).round(2).to_dict()
