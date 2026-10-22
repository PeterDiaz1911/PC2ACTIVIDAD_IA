from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def normalizar_texto(valor):
    if pd.isna(valor):
        return None
    texto = str(valor).strip()
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r'\s+', ' ', texto)
    return texto


def limpiar_cadenas(df: pd.DataFrame, columnas: Iterable[str]):
    for columna in columnas:
        if columna not in df.columns:
            continue
        df[columna] = df[columna].map(lambda x: normalizar_texto(x))
    return df


def mapear_binario(series: pd.Series):
    if series.empty:
        return pd.Series(dtype='Int64')
    valor = series.astype(str).str.strip().str.lower()
    valor = valor.map(lambda x: unicodedata.normalize('NFKD', x) if isinstance(x, str) else x)
    valor = valor.map(lambda x: ''.join(ch for ch in str(x) if not unicodedata.combining(ch)))
    mapa = {
        'si': 1, 's': 1, 'yes': 1, 'y': 1, 'true': 1, '1': 1,
        'no': 0, 'n': 0, 'false': 0, '0': 0,
    }
    return valor.map(lambda x: mapa.get(x, pd.NA)).astype('Int64')


def resolver_duplicados_usuario(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    if 'id_usuario' not in df.columns:
        return df, 0

    registros = []
    n_resueltos = 0
    for usuario, grupo in df.groupby('id_usuario', dropna=False):
        if len(grupo) == 1:
            registros.append(grupo)
            continue
        grupo = grupo.copy()
        grupo['completitud'] = grupo.notna().sum(axis=1)
        sort_cols = ['completitud']
        if 'fecha_registro' in grupo.columns:
            sort_cols.append('fecha_registro')
        grupo = grupo.sort_values(sort_cols, ascending=[False] * len(sort_cols), na_position='last')
        registros.append(grupo.iloc[[0]])
        n_resueltos += len(grupo) - 1

    resultado = pd.concat(registros, ignore_index=True) if registros else df.copy()
    resultado = resultado.drop(columns=['completitud'], errors='ignore')
    return resultado, n_resueltos


def limpiar_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    auditoria = []

    def registrar(problema: str, variable: str, cantidad: int, tratamiento: str, justificacion: str):
        auditoria.append({
            'problema': problema,
            'variable': variable,
            'cantidad_registros_afectados': int(cantidad),
            'tratamiento_aplicado': tratamiento,
            'justificacion': justificacion,
        })

    df = df.copy()
    columnas = {col: normalizar_texto(col) for col in df.columns}
    df = df.rename(columns=columnas)
    df = limpiar_cadenas(df, ['genero', 'pais', 'plan', 'metodo_pago', 'dispositivo_principal', 'genero_favorito'])

    ids_repetidos = int(df['id_usuario'].duplicated(keep='first').sum()) if 'id_usuario' in df.columns else 0
    exact_dupes = df.duplicated(keep='first')
    n_exact = int(exact_dupes.sum())
    df = df.loc[~exact_dupes].copy().reset_index(drop=True)
    registrar(
        'Duplicados exactos',
        'dataset',
        n_exact,
        'Se eliminó una copia de cada fila idéntica',
        f'Las filas idénticas no aportan información adicional. Los {ids_repetidos} id_usuario repetidos en el archivo original corresponden a estas copias exactas.',
    )

    df, n_usuario = resolver_duplicados_usuario(df)
    if n_usuario:
        registrar(
            'Mismo usuario con registros diferentes',
            'id_usuario',
            n_usuario,
            'Se conservó un registro por usuario, priorizando mayor completitud y luego fecha más reciente',
            'Los registros restantes del mismo usuario no eran idénticos. Se conservó una sola observación para evitar que el usuario aparezca en más de una partición.',
        )

    for columna in ['plan', 'pais', 'metodo_pago', 'dispositivo_principal', 'genero', 'genero_favorito']:
        if columna in df.columns:
            df[columna] = df[columna].map(lambda x: normalizar_texto(x))

    df['plan'] = df['plan'].replace({'BASICO': 'Basico', 'ESTANDAR': 'Estandar', 'PREMIUM': 'Premium'})
    df['plan'] = df['plan'].str.title()
    df['pais'] = df['pais'].str.title()
    df['genero'] = df['genero'].str.upper()
    df['metodo_pago'] = df['metodo_pago'].str.title()
    df['dispositivo_principal'] = df['dispositivo_principal'].str.title()
    df['genero_favorito'] = df['genero_favorito'].str.title()

    if 'cancelo' in df.columns:
        valores_invalidos = ~df['cancelo'].map(lambda x: str(normalizar_texto(x) or '').lower() in {'si', 's', 'yes', 'y', 'no', 'n', '1', '0', 'true', 'false'})
        n_target_invalid = int(valores_invalidos.sum())
        if n_target_invalid:
            registrar('Valores inesperados en cancelo', 'cancelo', n_target_invalid, 'Se marcó como ausente y se excluyó del modelado', 'La variable objetivo no debe imputarse; si el valor no está dentro de los estados válidos, no se puede aprender ni predecir sobre ese registro.')
        df['cancelo'] = mapear_binario(df['cancelo'])

    if 'usa_descargas' in df.columns:
        df['usa_descargas'] = mapear_binario(df['usa_descargas'])
        valores_invalidos = df['usa_descargas'].isna()
        if valores_invalidos.any():
            registrar('Valores inesperados en usa_descargas', 'usa_descargas', int(valores_invalidos.sum()), 'Se normalizó a Si/No y se dejó como nulo cuando no era válido', 'La variable de uso de descargas es categórica binaria y requiere consistencia antes de análisis posterior.')

    for columna, regla in {
        'edad': (lambda x: (x < 10) | (x > 100), 'Se reemplazó por nulo para evitar edades imposibles'),
        'horas_vistas_mes': (lambda x: (x < 0) | (x > 720), 'Se reemplazó por nulo porque los valores negativos o extremos no son coherentes con el comportamiento observado'),
        'calificacion_promedio': (lambda x: (x < 1) | (x > 5), 'Se marcó como faltante porque la escala de calificación es 1 a 5'),
        'pct_vistas_por_recomendacion': (lambda x: (x < 0) | (x > 100), 'Se trató como nulo porque el porcentaje debe estar en 0 a 100'),
        'precio_mensual_soles': (lambda x: x < 0, 'Se marcó como nulo para evitar precios negativos'),
        'meses_suscrito': (lambda x: (x < 0) | (x > 120), 'Los valores negativos o extremos no son plausibles para una suscripción'),
        'titulos_completados_mes': (lambda x: x < 0, 'No existen cantidades negativas de títulos completados'),
        'dias_desde_ultimo_acceso': (lambda x: x < 0, 'Los días desde el último acceso no pueden ser negativos'),
        'tickets_soporte': (lambda x: x < 0, 'Los tickets negativos no tienen sentido para la experiencia del cliente'),
    }.items():
        if columna in df.columns:
            original = df[columna]
            s = pd.to_numeric(df[columna], errors='coerce')
            conversiones_invalidas = int((original.notna() & s.isna()).sum())
            if conversiones_invalidas:
                registrar(
                    'Valor no numérico',
                    columna,
                    conversiones_invalidas,
                    'Se convirtió a nulo; se imputará dentro del pipeline si la variable entra al modelo',
                    'No se puede interpretar una cadena inválida como una medida numérica válida.',
                )
            mask = regla[0](s)
            n = int(mask.sum())
            if n:
                df[columna] = s.where(~mask, pd.NA)
                registrar(
                    'Rango inválido',
                    columna,
                    n,
                    regla[1],
                    'Se aplicó una regla determinista basada en el dominio del negocio y la escala esperada de cada variable.',
                )
            else:
                df[columna] = s

    if 'fecha_registro' in df.columns:
        fecha = pd.to_datetime(df['fecha_registro'], errors='coerce')
        invalidos = fecha.isna()
        if invalidos.any():
            registrar('Fechas inválidas', 'fecha_registro', int(invalidos.sum()), 'Se transformó a nulo', 'La fecha de registro debe estar en un formato temporal válido para cualquier análisis de antigüedad o ventana temporal.')
        df['fecha_registro'] = fecha

    df = df.reset_index(drop=True)
    audit_df = pd.DataFrame(auditoria)
    return df, audit_df


def cargar_y_limpiar(ruta_csv: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    ruta = Path(ruta_csv)
    df = pd.read_csv(ruta)
    df_limpio, auditoria = limpiar_dataframe(df)
    return df_limpio, auditoria


def exportar_datos_limpios(df: pd.DataFrame, auditoria: pd.DataFrame, ruta_csv: str | Path) -> pd.DataFrame:
    ruta = Path(ruta_csv)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False)
    auditoria.to_csv(ruta.parent / 'auditoria_limpieza_netflix.csv', index=False)
    return df


def main() -> None:
    raw_path = ROOT / 'data' / 'raw' / 'neflix.csv'
    clean_path = ROOT / 'data' / 'processed' / 'netflix_limpio.csv'
    df, auditoria = cargar_y_limpiar(raw_path)
    exportar_datos_limpios(df, auditoria, clean_path)
    print(f'Archivo limpio guardado en: {clean_path}')
    print(f'Filas finales: {len(df)}')
    print(auditoria.to_string(index=False))


if __name__ == '__main__':
    main()
