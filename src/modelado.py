from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.dummy import DummyClassifier

ROOT = Path(__file__).resolve().parents[1]
MODEL_VERSION = '1.0.0'


def preparar_dataset(df: pd.DataFrame, target: str = 'cancelo') -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    model_df = df.dropna(subset=[target]).copy()
    excluded = [column for column in ('id_usuario', 'fecha_registro') if column in model_df.columns]
    X = model_df.drop(columns=[target, *excluded])
    y = model_df[target].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )
    return X_train, y_train, X_test, y_test


def construir_preprocesador(X: pd.DataFrame):
    numericas = X.select_dtypes(include=['number']).columns.tolist()
    categoricas = X.select_dtypes(exclude=['number']).columns.tolist()
    transformers = []
    if numericas:
        transformers.append(('num', Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler()),
        ]), numericas))
    if categoricas:
        transformers.append(('cat', Pipeline([
            ('imputer', SimpleImputer(strategy='most_frequent')),
            ('onehot', OneHotEncoder(handle_unknown='ignore')),
        ]), categoricas))
    return ColumnTransformer(transformers=transformers, remainder='drop')


def entrenar_modelos(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    X_train, y_train, X_test, y_test = preparar_dataset(df)
    preprocesador = construir_preprocesador(X_train)

    modelos = {
        'DummyClassifier': DummyClassifier(strategy='most_frequent'),
        'LogisticRegression': LogisticRegression(max_iter=2000, random_state=42),
        'RandomForestClassifier': RandomForestClassifier(n_estimators=300, random_state=42),
    }

    resultados = []
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    for nombre, modelo in modelos.items():
        pipeline = Pipeline([
            ('preprocesador', preprocesador),
            ('modelo', modelo),
        ])
        cv_scores = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring='f1')
        pipeline.fit(X_train, y_train)
        pred = pipeline.predict(X_test)
        metricas = {
            'modelo': nombre,
            'accuracy': accuracy_score(y_test, pred),
            'precision': precision_score(y_test, pred, zero_division=0),
            'recall': recall_score(y_test, pred, zero_division=0),
            'f1': f1_score(y_test, pred, zero_division=0),
            'train_cv_f1_mean': float(cv_scores.mean()),
            'train_cv_f1_std': float(cv_scores.std()),
        }
        resultados.append(metricas)

        report = classification_report(y_test, pred, output_dict=True, zero_division=0)
        cm = confusion_matrix(y_test, pred)
        ruta_metrics = ROOT / 'reports' / 'metrics' / f'{nombre.lower()}_report.json'
        ruta_metrics.parent.mkdir(parents=True, exist_ok=True)
        with open(ruta_metrics, 'w', encoding='utf-8') as fh:
            json.dump({
                'classification_report': report,
                'confusion_matrix': cm.tolist(),
                'confusion_matrix_labels': ['No cancelo (0)', 'Sí cancelo (1)'],
                'positive_class': 1,
                'test_rows': int(len(y_test)),
                'test_class_counts': {str(int(k)): int(v) for k, v in y_test.value_counts().sort_index().items()},
            }, fh, ensure_ascii=False, indent=2)
        fig, ax = plt.subplots(figsize=(5, 4))
        image = ax.imshow(cm, cmap='Blues')
        ax.set_title(f'Matriz de confusión: {nombre}')
        ax.set_xlabel('Predicción')
        ax.set_ylabel('Valor real')
        ax.set_xticks([0, 1], labels=['No cancelo', 'Sí cancelo'])
        ax.set_yticks([0, 1], labels=['No cancelo', 'Sí cancelo'])
        for (row, column), value in np.ndenumerate(cm):
            ax.text(column, row, str(value), ha='center', va='center')
        fig.colorbar(image, ax=ax, label='Usuarios')
        fig.tight_layout()
        matrix_path = ROOT / 'reports' / 'figures' / f'matriz_confusion_{nombre.lower()}.png'
        matrix_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(matrix_path, dpi=180)
        plt.close(fig)

    tabla = pd.DataFrame(resultados).sort_values('f1', ascending=False).reset_index(drop=True)
    tabla.to_csv(ROOT / 'reports' / 'metrics' / 'metricas_modelos.csv', index=False)

    referencia = max(resultados, key=lambda resultado: resultado['train_cv_f1_mean'])['modelo']
    modelo_escogido = modelos[referencia]
    pipeline_escogido = Pipeline([
        ('preprocesador', preprocesador),
        ('modelo', modelo_escogido),
    ])
    pipeline_escogido.fit(X_train, y_train)
    model_dir = ROOT / 'reports' / 'models'
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / 'netflix_churn_pipeline.joblib'
    joblib.dump(pipeline_escogido, model_path)

    input_schema = []
    for column in X_train.columns:
        if pd.api.types.is_numeric_dtype(X_train[column]):
            input_schema.append({
                'name': column,
                'kind': 'number',
                'minimum': _finite_bound(X_train[column].min()),
                'maximum': _finite_bound(X_train[column].max()),
                'required': True,
            })
        else:
            categories = sorted(str(value) for value in X_train[column].dropna().unique())
            input_schema.append({
                'name': column,
                'kind': 'category',
                'options': categories,
                'required': True,
            })

    importancia = permutation_importance(
        pipeline_escogido,
        X_train,
        y_train,
        n_repeats=10,
        random_state=42,
        scoring='f1',
    )
    features = X_test.columns.tolist()
    importancias = pd.DataFrame({'variable': features, 'importancia_media': importancia.importances_mean})
    importancias = importancias.sort_values('importancia_media', ascending=False).head(15).reset_index(drop=True)
    importancias.to_csv(ROOT / 'reports' / 'metrics' / 'variables_importantes.csv', index=False)

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(importancias['variable'], importancias['importancia_media'], color='#4c78a8')
    ax.invert_yaxis()
    ax.set_title('Variables más importantes para la predicción de cancelación')
    ax.set_xlabel('Importancia por permutación (F1)')
    fig.tight_layout()
    fig.savefig(ROOT / 'reports' / 'figures' / 'variables_importantes.png', dpi=180)
    plt.close(fig)

    evaluation = {
        'source': 'data/raw/neflix.csv',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'model_version': MODEL_VERSION,
        'model_artifact': 'reports/models/netflix_churn_pipeline.joblib',
        'threshold': 0.5,
        'input_schema': input_schema,
        'split': {'train_fraction': 0.75, 'test_fraction': 0.25, 'random_state': 42, 'stratified': True},
        'excluded_predictors': {
            'id_usuario': 'Identificador; no aporta una señal generalizable y podría memorizar usuarios.',
            'fecha_registro': 'No hay fecha de corte documentada; no se calcula antigüedad ni se usa como predictor.',
        },
        'positive_class': 1,
        'test_rows': int(len(y_test)),
        'test_class_counts': {str(int(k)): int(v) for k, v in y_test.value_counts().sort_index().items()},
        'models': resultados,
        'selected_for_permutation_importance': referencia,
        'permutation_importance': {
            'dataset': 'entrenamiento',
            'scoring': 'f1',
            'interpretation': 'La importancia predictiva no demuestra causalidad.',
        },
        'temporal_limitation': (
            'El CSV no documenta cuándo se midieron las variables respecto a la cancelación. '
            'Para una predicción futura, solo deben usarse variables disponibles antes de cancelar.'
        ),
    }
    with open(ROOT / 'reports' / 'metrics' / 'evaluation_netflix.json', 'w', encoding='utf-8') as fh:
        json.dump(evaluation, fh, ensure_ascii=False, indent=2)

    return tabla, importancias


def _finite_bound(value):
    if pd.isna(value):
        return None
    number = float(value)
    return number if np.isfinite(number) else None


def main() -> None:
    df = pd.read_csv(ROOT / 'data' / 'processed' / 'netflix_limpio.csv')
    tabla, importancias = entrenar_modelos(df)
    print(tabla.to_string(index=False))
    print('\nTop variables:')
    print(importancias.head().to_string(index=False))


if __name__ == '__main__':
    main()
