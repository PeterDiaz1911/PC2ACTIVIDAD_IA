from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]


def tasa_cancelacion(df: pd.DataFrame, agrupacion: str | None = None) -> pd.DataFrame:
    if agrupacion is None:
        total = df['cancelo'].dropna().shape[0]
        cancelados = int(df['cancelo'].dropna().sum())
        return pd.DataFrame({'grupo': ['Total'], 'usuarios': [total], 'cancelados': [cancelados], 'tasa_cancelacion': [cancelados / total if total else 0]})

    tabla = df.groupby(agrupacion, dropna=False)['cancelo'].agg(['count', 'sum']).reset_index()
    tabla.columns = [agrupacion, 'usuarios', 'cancelados']
    tabla[agrupacion] = tabla[agrupacion].fillna('Sin dato')
    tabla['tasa_cancelacion'] = tabla['cancelados'] / tabla['usuarios']
    return tabla


def interpretacion_tasa(tabla: pd.DataFrame, variable: str) -> str:
    if tabla.empty:
        return f'No hay usuarios con objetivo válido para analizar {variable}.'
    top = tabla.sort_values(['tasa_cancelacion', 'usuarios'], ascending=[False, False]).iloc[0]
    return (
        f'{top[variable]} presenta la tasa observada más alta '
        f'({top["tasa_cancelacion"]:.1%}; {int(top["cancelados"])} de {int(top["usuarios"])} usuarios). '
        'La tasa es descriptiva y no implica causalidad.'
    )


def guardar_figura(fig, ruta: str | Path):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(ruta, bbox_inches='tight', dpi=180)
    plt.close(fig)


def generar_graficos_exploratorios(df: pd.DataFrame, output_dir: str | Path) -> list[Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []

    sns.set_theme(style='whitegrid')

    fig, ax = plt.subplots(figsize=(6, 4))
    cuenta = df['cancelo'].dropna().value_counts().sort_index()
    labels = ['No', 'Sí']
    ax.bar(labels, [cuenta.get(0, 0), cuenta.get(1, 0)], color=['#4c78a8', '#f58518'])
    ax.set_title('Distribución de cancelaciones')
    ax.set_ylabel('Usuarios')
    paths.append(output_dir / '01_distribucion_cancelaciones.png')
    guardar_figura(fig, paths[-1])

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    tabla = tasa_cancelacion(df, 'plan').sort_values('tasa_cancelacion', ascending=False)
    bars = ax.bar(tabla['plan'], tabla['tasa_cancelacion'] * 100, color='#4c78a8')
    ax.set_title('Tasa de cancelación por plan')
    ax.set_ylabel('% cancelación')
    ax.set_xlabel('Plan')
    ax.set_ylim(0, 100)
    for bar, (_, row) in zip(bars, tabla.iterrows()):
        ax.annotate(f'{row["tasa_cancelacion"]:.1%}\nn={int(row["usuarios"])}', (bar.get_x() + bar.get_width() / 2, bar.get_height()), ha='center', va='bottom', fontsize=8)
    paths.append(output_dir / '02_tasa_cancelacion_plan.png')
    guardar_figura(fig, paths[-1])

    fig, ax = plt.subplots(figsize=(8, 5))
    tabla = tasa_cancelacion(df, 'pais').sort_values('tasa_cancelacion', ascending=False).head(10)
    ax.bar(tabla['pais'], tabla['tasa_cancelacion'] * 100, color='#4c78a8')
    ax.set_title('Tasa de cancelación por país')
    ax.set_ylabel('% cancelación')
    ax.set_xlabel('País')
    ax.tick_params(axis='x', rotation=45)
    for bar, (_, row) in zip(ax.patches, tabla.iterrows()):
        ax.annotate(f'{row["tasa_cancelacion"]:.1%}\nn={int(row["usuarios"])}', (bar.get_x() + bar.get_width() / 2, bar.get_height()), ha='center', va='bottom', fontsize=8)
    paths.append(output_dir / '03_tasa_cancelacion_pais.png')
    guardar_figura(fig, paths[-1])

    fig, ax = plt.subplots(figsize=(8, 5))
    tabla = tasa_cancelacion(df, 'metodo_pago').sort_values('tasa_cancelacion', ascending=False)
    ax.bar(tabla['metodo_pago'], tabla['tasa_cancelacion'] * 100, color='#4c78a8')
    ax.set_title('Tasa de cancelación por método de pago')
    ax.set_ylabel('% cancelación')
    ax.set_xlabel('Método de pago')
    ax.tick_params(axis='x', rotation=30)
    for bar, (_, row) in zip(ax.patches, tabla.iterrows()):
        ax.annotate(f'{row["tasa_cancelacion"]:.1%}\nn={int(row["usuarios"])}', (bar.get_x() + bar.get_width() / 2, bar.get_height()), ha='center', va='bottom', fontsize=8)
    paths.append(output_dir / '04_tasa_cancelacion_metodo_pago.png')
    guardar_figura(fig, paths[-1])

    fig, ax = plt.subplots(figsize=(8, 5))
    tabla = tasa_cancelacion(df, 'dispositivo_principal').sort_values('tasa_cancelacion', ascending=False)
    ax.bar(tabla['dispositivo_principal'], tabla['tasa_cancelacion'] * 100, color='#4c78a8')
    ax.set_title('Tasa de cancelación por dispositivo')
    ax.set_ylabel('% cancelación')
    ax.set_xlabel('Dispositivo principal')
    for bar, (_, row) in zip(ax.patches, tabla.iterrows()):
        ax.annotate(f'{row["tasa_cancelacion"]:.1%}\nn={int(row["usuarios"])}', (bar.get_x() + bar.get_width() / 2, bar.get_height()), ha='center', va='bottom', fontsize=8)
    paths.append(output_dir / '05_tasa_cancelacion_dispositivo.png')
    guardar_figura(fig, paths[-1])

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    variables = ['horas_vistas_mes', 'dias_desde_ultimo_acceso', 'calificacion_promedio', 'tickets_soporte']
    for ax, var in zip(axes.flat, variables):
        datos = df[[var, 'cancelo']].dropna()
        datos = datos.assign(cancelacion=datos['cancelo'].map({0: 'No cancela', 1: 'Sí cancela'}))
        sns.boxplot(data=datos, x='cancelacion', y=var, hue='cancelacion', palette={'No cancela': '#4c78a8', 'Sí cancela': '#f58518'}, ax=ax, dodge=False, legend=False)
        ax.set_title(f'{var} según cancelación')
        ax.set_xlabel('Estado de cancelación')
        ax.set_ylabel(var.replace('_', ' '))
    paths.append(output_dir / '06_comparacion_cancelacion.png')
    guardar_figura(fig, paths[-1])

    return paths


def main():
    df = pd.read_csv(ROOT / 'data' / 'processed' / 'netflix_limpio.csv')
    generar_graficos_exploratorios(df, ROOT / 'reports' / 'figures')
    print('Gráficos exportados a reports/figures/')


if __name__ == '__main__':
    main()
