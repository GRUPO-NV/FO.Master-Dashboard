# Family Office — Panel Consolidado

Dashboard interactivo (Streamlit + Plotly) sobre `FO_Master_Consolidado.xlsx`: patrimonio
consolidado, inversiones, bienes raíces, empresas vinculadas, flujo de caja y KPIs de un
grupo familiar de alto patrimonio en Chile. Va más allá del Excel: agrega drill-down,
semáforos de riesgo, un checklist de datos pendientes generado automáticamente, un
simulador de escenarios de apalancamiento y un historial de patrimonio neto.

## Requisitos

- Python 3.11+
- **LibreOffice** (`soffice`) instalado y en el `PATH` — se usa para recalcular las
  fórmulas del Excel antes de leerlo (ver más abajo). En Debian/Ubuntu:
  `apt-get install libreoffice-calc`

## Instalación

```bash
pip install -r requirements.txt
```

Copia el archivo fuente a `data/FO_Master_Consolidado.xlsx` (ya incluido en este repo).

## Ejecutar

```bash
streamlit run app.py
```

## Por qué se recalcula con LibreOffice

El Excel tiene fórmulas, no solo valores. Si el archivo fue editado a mano, las celdas
con fórmulas pueden no traer el resultado cacheado, y `openpyxl` con `data_only=True`
las leería como `None`. `src/excel_recalc.py` resuelve esto invocando
`soffice --headless --convert-to xlsx` para forzar el recálculo antes de leer el
archivo. No hay un proceso "watcher" separado: `src/app_data.py` usa la fecha de
modificación del archivo fuente como clave de caché de Streamlit, así que cualquier
actualización del Excel dispara un recálculo automático en el siguiente rerun (por
ejemplo, al recargar la página en el navegador).

## Arquitectura

La lectura y el parseo del Excel están completamente aislados de la UI, para que una
futura migración a Next.js + FastAPI sea directa:

- `src/excel_recalc.py` — recalcula el Excel con LibreOffice headless (con caché por
  fecha de modificación).
- `src/data_loader.py` — parsea las 13 pestañas a dataframes/dataclasses limpios
  (`FOData`). Es el único módulo que conoce la estructura de filas/columnas del Excel.
- `src/kpi_engine.py` — arma las tarjetas de KPI con semáforo (verde/amarillo/rojo)
  según umbrales documentados en el propio código.
- `src/pending_data.py` — escanea `FOData` en busca de datos faltantes o proxys
  (patrimonio contable sin cargar, tasación comercial faltante, titulares sin
  confirmar, egresos atípicos en el flujo de caja, etc.) y arma un checklist priorizado.
- `src/simulator.py` — motor del simulador de escenarios (apalancamiento sobre Bienes
  Raíces, costo de deuda, retorno reinvertido, horizonte).
- `src/pdf_export.py` — genera el PDF de resumen ejecutivo.
- `src/snapshots.py` — guarda un registro de Patrimonio Neto por versión del Excel
  para el historial.
- `src/theme.py` — paleta, helpers de formato (CLP/%) y componentes de UI compartidos.
- `src/app_data.py` — caché de Streamlit sobre `data_loader`, con recarga automática
  cuando cambia el archivo fuente.
- `app.py` + `pages/` — la aplicación Streamlit (una página por área del dashboard).

## Notas sobre los datos

- El Excel trae dos bases de valorización de Bienes Raíces: Avalúo Fiscal (SII, para
  contribuciones) y Tasación Comercial (para el Balance). Donde falta la tasación
  real, el dashboard usa Avalúo Fiscal × factor (parámetro en `Supuestos`), igual que
  el Excel — y además completa 2 propiedades cuyo "Valor Balance"/"Valor Atribuible"
  venían en blanco en el archivo original (ver panel **Datos Pendientes**).
- La fila "Saldo Acumulado" de la grilla mensual de Flujo de Caja venía vacía en el
  archivo fuente. El dashboard la reconstruye como suma acumulada del Saldo Mensual,
  anclada al valor conocido de la tabla "Resumen Anual" en oct-2026 — queda marcado
  como dato reconstruido en la página de Flujo de Caja y en Datos Pendientes.
- El simulador de escenarios reproduce exactamente el KPI "Patrimonio Neto proyectado"
  del Excel cuando el apalancamiento está en 0%; esto sirve como validación cruzada
  del modelo.

## Snapshots e historial

`data/snapshots.csv` (no versionado) acumula un registro por cada versión distinta del
Excel que se carga. Con al menos 2 snapshots, la página **Historial** grafica la
evolución del Patrimonio Neto.
