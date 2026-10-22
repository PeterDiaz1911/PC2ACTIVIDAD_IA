# Netflix Churn Analytics

Dashboard local para analizar cancelaciones de suscripciones del caso académico “¿Quién va a cancelar Netflix?”. Es un proyecto académico no oficial y no está afiliado con Netflix. No reproduce contenido multimedia.

El único origen de datos es `data/raw/neflix.csv` (se conserva su nombre original). La aplicación no consulta servicios externos ni depende de Google Colab.

## Requisitos

- Windows 10/11, PowerShell y Node.js/npm.
- Python 3.10 o posterior.
- El CSV original en `data/raw/neflix.csv`.

## Instalación desde PowerShell

Ejecuta los comandos desde la raíz del proyecto:

```powershell
npm install
npm run install:python
```

`npm install` instala Vite, React, Bootstrap, gráficos y las herramientas de inicio. `npm run install:python` crea `.venv` si hace falta, instala `requirements.txt` y verifica dependencias con `pip check`. Son instalaciones independientes; npm no instala paquetes Python.

## Inicio local

Desde la raíz del proyecto:

```powershell
npm run dev
```

Abre <http://127.0.0.1:5173>. Vite reenvía `/api` a FastAPI en <http://127.0.0.1:8000>. Si el puerto 8000 ya está ocupado, el script identifica el PID/comando y se detiene sin cerrar procesos ajenos. Vite también falla explícitamente si el puerto 5173 está ocupado.

Comandos alternativos, también desde la raíz:

```powershell
npm run dev:frontend
npm run dev:backend
npm run build
npm test
npm run analysis
```

- `dev:frontend`: inicia solo Vite.
- `dev:backend`: inicia solo FastAPI/Uvicorn con `.venv`.
- `build`: ejecuta TypeScript y genera `frontend/dist/`.
- `test`: ejecuta las pruebas de limpieza, pipeline y API con pytest.
- `analysis`: limpia los datos, genera gráficos y tablas, compara los modelos, guarda el pipeline entrenado y crea la presentación. No se ejecuta al abrir la web ni al solicitar una predicción.

## Notebook

El entregable independiente es `notebooks/01_netflix_cancelaciones.ipynb`. Selecciona el kernel `.venv` (`.venv\Scripts\python.exe`) y ejecuta las celdas en orden. El notebook invoca `src.analisis.ejecutar_analisis`, la misma entrada compartida por `npm run analysis`, y presenta los artefactos que esa ejecución genera.

Para identificar el intérprete y comprobar el kernel desde la raíz:

```powershell
.\.venv\Scripts\python.exe -c "import sys, zmq, ipykernel; print(sys.executable); print('pyzmq', zmq.__version__, 'ipykernel', ipykernel.__version__)"
.\.venv\Scripts\python.exe -m jupyter kernelspec list
```

El kernel instalado para este proyecto apunta a `.venv`. Si Jupyter informa `ZMQError: Permission denied`, comprueba primero que VS Code ejecuta ese kernel y que no hay una política de seguridad local bloqueando la creación de sockets del proceso. No desactives antivirus/firewall ni eleves privilegios como solución general; revisa los registros y las políticas del equipo. La ejecución del CLI (`npm run analysis`) no necesita un kernel Jupyter.

## Salidas del análisis

- `data/processed/netflix_limpio.csv` y `data/processed/auditoria_limpieza_netflix.csv`.
- `reports/figures/`: tasas por segmentos, comparaciones de comportamiento, importancia y matrices de confusión.
- `reports/metrics/`: métricas de LogisticRegression/RandomForestClassifier, evaluación, partición y versión/fecha/origen de datos.
- `reports/models/netflix_churn_pipeline.joblib`: pipeline completo con preprocesamiento y modelo.
- `reports/presentacion_netflix.pptx`: presentación independiente de la web.

La clase positiva es `cancelo=1`. Las métricas describen la partición de prueba y no cambian con los filtros del dashboard. La predicción individual solo aparece cuando existe un pipeline guardado; la puntuación no calibrada no es certeza. La disponibilidad temporal de las variables debe validarse: asociación predictiva no implica causalidad.

## API y descargas

FastAPI publica estado, resumen, calidad, filtros/segmentos, métricas, factores, predicción (si hay modelo) y descargas por identificadores permitidos. No acepta rutas de archivos arbitrarias. Si faltan resultados, la aplicación informa “Análisis pendiente”; desde la raíz ejecuta `npm run analysis`.

## Publicación en internet

La configuración `vercel.json` publica el frontend Vite y la API FastAPI como **Services** en un único proyecto Vercel: `/api/*` se enruta a `pcactividad-ia-api` y el resto de las rutas a `frontend`. GitHub Pages no puede ejecutar el backend de Python.

1. En Vercel, importa este repositorio y selecciona **Services** para desplegar las aplicaciones detectadas en un solo proyecto; no las importes como proyectos independientes.
2. Mantén la raíz de configuración en la raíz del repositorio para que Vercel lea `vercel.json`. Despliega ambos servicios y abre el dominio asignado al proyecto.
3. La web ya usa `/api` en el mismo dominio; no hace falta configurar `VITE_API_BASE_URL` ni un binding de servicio.

Como alternativa separada, `render.yaml` permite alojar la API en Render. En ese caso, configura `VITE_API_BASE_URL` en Vercel con la URL de Render seguida de `/api` y `FRONTEND_ORIGINS` en Render con el dominio de la web. En Render gratuito, la API puede tardar unos segundos en responder después de un periodo sin uso.

## Google Colab

El error `TypeError: Failed to fetch` cuya traza procede de `colaboratory-static` no se puede reproducir ni verificar sin acceso a la sesión de Colab. No se atribuye a ZMQ o npm. La ejecución local de esta aplicación y su pipeline no dependen de Colab.
