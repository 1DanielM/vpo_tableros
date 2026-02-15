import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import altair as alt
import locale
import traceback
import plotly.graph_objects as go # <--- NUEVA IMPORTACIÓN DE PLOTLY

# ---------------------------
# Helpers y configuración
# ---------------------------
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza columnas: strip, upper, reemplaza espacios por guion bajo, y corrige %_EJECUCION."""
    df = df.copy()
    # Normalización estándar
    df.columns = df.columns.astype(str).str.strip().str.upper().str.replace(" ", "_")
    
    # Corrección específica para el archivo de componentes (o cualquier DF)
    if "%_EJECUCION" in df.columns:
        df = df.rename(columns={"%_EJECUCION": "PORCENTAJE_EJECUCION"})
    return df


def fmt_money(v):
    """Formatea valores grandes usando separador de miles (cifra completa)."""
    try:
        return f"{v:,.0f}"
    except Exception:
        return f"{v}"


def fmt_pct(v):
    """Formatea valores como porcentaje."""
    try:
        return f"{v:,.2f}%"
    except Exception:
        return f"{v}"


# =========================================================================
# --- FUNCIÓN DE AGREGACIÓN PARA LA TABLA DE COMPONENTES ---
# =========================================================================

def create_componente_table(df: pd.DataFrame):
    """
    Calcula Presupuesto, Ejecutado, Diferencia y % Ejecución
    agregados por la columna 'CONCEPTO', e incluye una fila de totales.
    Retorna (df_display, df_export) o None si no hay datos.
    """
    # Si no hay columna de CONCEPTO o está vacía/inútil, retornar None
    if "CONCEPTO" not in df.columns or df["CONCEPTO"].nunique() == 0 or (df["CONCEPTO"] == "N/A").all():
        return None

    # 1. Agrupar y agregar por CONCEPTO
    df_group = df.groupby("CONCEPTO").agg(
        PRESUPUESTO=("PRESUPUESTO", "sum"),
        EJECUTADO=("EJECUTADO", "sum"),
    ).reset_index()

    # 2. Recalcular métricas a nivel de concepto
    df_group["DIFERENCIA"] = df_group["EJECUTADO"] - df_group["PRESUPUESTO"]
    df_group["PORCENTAJE_EJECUCION"] = (df_group["EJECUTADO"] / df_group["PRESUPUESTO"])
    df_group["PORCENTAJE_EJECUCION"] = df_group["PORCENTAJE_EJECUCION"].replace([np.inf, -np.inf], 0).fillna(0) * 100

    # 3. Calcular la fila de totales
    total_row = pd.DataFrame([{
        "CONCEPTO": "TOTAL",
        "PRESUPUESTO": df_group["PRESUPUESTO"].sum(),
        "EJECUTADO": df_group["EJECUTADO"].sum(),
    }])
    total_presupuesto = total_row["PRESUPUESTO"].iloc[0]
    total_ejecutado = total_row["EJECUTADO"].iloc[0]
    
    # Recalcular la Diferencia y el % Ejecución para el TOTAL
    total_row["DIFERENCIA"] = total_ejecutado - total_presupuesto
    total_pct_ejecucion = (total_ejecutado / total_presupuesto) * 100 if total_presupuesto != 0 else 0
    total_row["PORCENTAJE_EJECUCION"] = total_pct_ejecucion

    # 4. Combinar grupo y total (Esto crea el DF_EXPORT intermedio con valores numéricos)
    df_export_num = pd.concat([df_group, total_row], ignore_index=True)

    # 5. Renombrar columnas para display/export
    # Aquí es donde 'DIFERENCIA' se convierte en 'Diferencia'
    df_export = df_export_num.rename(columns={
        "DIFERENCIA": "Diferencia",
        "PORCENTAJE_EJECUCION": "% Ejecución"
    })

    # Seleccionar y reordenar columnas
    df_export = df_export[["CONCEPTO", "PRESUPUESTO", "EJECUTADO", "Diferencia", "% Ejecución"]]

    # Preparar DF para Display (valores formateados)
    df_display = df_export.copy()
    df_display = df_display.rename(columns={"CONCEPTO": "Concepto"})

    # Aplicar formato.
    df_display["Presupuesto"] = df_display["PRESUPUESTO"].apply(fmt_money)
    df_display["Ejecutado"] = df_display["EJECUTADO"].apply(fmt_money)
    
    # *** CORRECCIÓN CRÍTICA DE KEYERROR ***
    # Usamos "Diferencia" que es el nombre ya renombrado en df_export
    df_display["Diferencia"] = df_display["Diferencia"].apply(fmt_money)
    df_display["% Ejecución"] = df_display["% Ejecución"].apply(fmt_pct)
    
    # Eliminar las columnas numéricas intermedias antes del display (si se quiere)
    df_display = df_display.drop(columns=["PRESUPUESTO", "EJECUTADO"], errors="ignore")

    # ** LÍNEA CRÍTICA: Establece el orden de las columnas formateadas **
    df_display = df_display[["Concepto", "Presupuesto", "Ejecutado", "Diferencia", "% Ejecución"]]


    return df_display, df_export

# =========================================================================
# --- FUNCIÓN DE AGREGACIÓN PARA TABLAS DE DETALLE (Reutilizada)
# =========================================================================
def create_kpi_table(df: pd.DataFrame, group_col: str):
    """Calcula Presupuesto, Ejecutado, Diferencia y % Ejecución agregados por una columna."""
    if group_col not in df.columns or df[group_col].nunique() == 0 or (df[group_col] == "N/A").all():
        return None

    df_group = df[df[group_col] != "N/A"].groupby(group_col).agg({
        "TOTAL_PRESUPUESTO": "sum",
        "TOTAL_EJECUTADO": "sum"
    }).reset_index()

    if df_group.empty:
        return None

    df_group["Diferencia"] = df_group["TOTAL_EJECUTADO"] - df_group["TOTAL_PRESUPUESTO"]
    df_group["% Ejecución"] = (df_group["TOTAL_EJECUTADO"] / df_group["TOTAL_PRESUPUESTO"])
    df_group["% Ejecución"] = df_group["% Ejecución"].replace([np.inf, -np.inf], 0).fillna(0) * 100

    df_export = df_group.rename(columns={
        "TOTAL_PRESUPUESTO": "Presupuesto",
        "TOTAL_EJECUTADO": "Ejecutado",
        group_col: group_col
    })

    df_display = df_export.copy()

    if group_col == "MES" and "FECHA" in df.columns:
        meses_orden = {
            'ENE': 1, 'FEB': 2, 'MAR': 3, 'ABR': 4, 'MAY': 5, 'JUN': 6,
            'JUL': 7, 'AGO': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DIC': 12
        }
        df_display["MES_ORDER"] = df_display["MES"].astype(str).str.upper().map(meses_orden)
        df_display = df_display.dropna(subset=["MES_ORDER"])
        df_display = df_display.sort_values(by="MES_ORDER").drop(columns=["MES_ORDER"])


    df_display = df_display.rename(columns={group_col: group_col.replace("_", " ").title()})
    df_display["Presupuesto"] = df_display["Presupuesto"].apply(fmt_money)
    df_display["Ejecutado"] = df_display["Ejecutado"].apply(fmt_money)
    df_display["Diferencia"] = df_display["Diferencia"].apply(fmt_money)
    df_display["% Ejecución"] = df_display["% Ejecución"].apply(fmt_pct)

    return df_display, df_export
# =========================================================================


# ---------------------------
# Ejecutable de la página
# ---------------------------
def mostrar_ingreso():
    # --- INYECCIÓN CSS PARA REDUCIR TAMAÑO DE FUENTE EN st.metric ---
    st.markdown("""
        <style>
        /* Target the value component of st.metric and reduce font size */
        div[data-testid="stMetricValue"] {
            font-size: 1.4rem; /* Tamaño reducido para los números grandes */
        }
        </style>
    """, unsafe_allow_html=True)
    # -----------------------------------------------------------------

    st.markdown("## Tablero de seguimiento - Ejecucion del Ingreso UPC")
    st.markdown("---")

    # ---------- Rutas ----------
    # ASEGÚRATE DE QUE ESTAS RUTAS SON CORRECTAS EN TU ENTORNO
    BASE_DIR = Path("C:/Users/dmendozad/Documents/Py/DATOS")
    RUTA_PRINCIPAL = BASE_DIR / "informes_vpo.xlsx"
    RUTA_GEO = BASE_DIR / "territorialidad_por_municipio_v5.xlsx"
    RUTA_COMPONENTES = RUTA_PRINCIPAL # Apunta al mismo archivo que la principal


    # ---------- Carga de datos (cache) ----------
    @st.cache_data(show_spinner=True)
    def cargar_datos(ruta_princ: Path, ruta_geo: Path, ruta_comp: Path):
        resultados = {"df_poblacion": pd.DataFrame(), "df_geo": pd.DataFrame(), "df_comp": pd.DataFrame(), "error": None}

        # 1. Carga de datos principales (ingreso)
        try:
            df = pd.read_excel(ruta_princ, sheet_name="ingreso")
            df = normalize_columns(df)
            resultados["df_poblacion"] = df
        except Exception as e:
            resultados["error"] = f"Error cargando {ruta_princ} (ingreso): {e}"
            return resultados

        # 2. Carga de datos de componentes
        try:
            dfcomp = pd.read_excel(ruta_comp, sheet_name="componentes")
            dfcomp = normalize_columns(dfcomp)
            resultados["df_comp"] = dfcomp
        except Exception as e:
            # Si falla, se carga un DF vacío
            resultados["df_comp"] = pd.DataFrame()
            resultados["comp_error"] = f"No se pudo cargar archivo componentes: {e}"

        # 3. Carga de datos geo
        try:
            dfgeo = pd.read_excel(ruta_geo, sheet_name="cobertura_eps")
            dfgeo = normalize_columns(dfgeo)
            resultados["df_geo"] = dfgeo
        except Exception as e:
            resultados["df_geo"] = pd.DataFrame()
            resultados["geo_error"] = f"No se pudo cargar archivo geo: {e}"

        return resultados

    carga = cargar_datos(RUTA_PRINCIPAL, RUTA_GEO, RUTA_COMPONENTES)
    if carga.get("error"):
        st.error(carga["error"])
        st.stop()

    df_poblacion = carga["df_poblacion"]
    df_geo = carga["df_geo"]
    df_componentes = carga["df_comp"]


    # ---------- Validaciones mínimas y Pre-procesamiento (VPO) ----------
    if df_poblacion.empty:
        st.warning("El archivo de datos VPO está vacío o no se cargó correctamente.")
        st.stop()

    expected_cols = [
        "ANO", "MES", "REGIMEN", "DANE",
        "TOTAL_PRESUPUESTO", "TOTAL_EJECUTADO",
        "PRESUPUESTO_UPC_LMA", "EJECUTADO_UPC_LMA",
        "PRESUPUESTO_PYP", "EJECUTADO_PYP",
        "PRESUPUESTO_PROVISION", "EJECUTADO_PROVISION"
    ]

    for col in expected_cols:
        if col not in df_poblacion.columns:
            if any(k in col for k in ["TOTAL", "PRESUPUESTO", "EJECUTADO"]):
                df_poblacion[col] = 0
            else:
                df_poblacion[col] = "N/A"

    monto_cols = [c for c in df_poblacion.columns if any(k in c for k in ["TOTAL", "PRESUPUESTO", "EJECUTADO"]) ]
    for c in monto_cols:
        # Aseguramos que la columna sea numérica y rellenamos NaNs con 0
        df_poblacion[c] = pd.to_numeric(df_poblacion.get(c, pd.Series([0])), errors="coerce").fillna(0)

    # -----------------------------------------------------------
    # Ajuste de FECHA
    # -----------------------------------------------------------
    try:
        locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'es_ES')
        except locale.Error:
            pass

    mapeo_meses = {
        'ENE': 1, 'FEB': 2, 'MAR': 3, 'ABR': 4, 'MAY': 5, 'JUN': 6,
        'JUL': 7, 'AGO': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DIC': 12
    }
    df_poblacion["MES_STR"] = df_poblacion["MES"].astype(str).str.upper().str.strip()
    df_poblacion["MES_NUM"] = df_poblacion["MES_STR"].map(mapeo_meses)
    valid_rows = df_poblacion["ANO"].astype(str).str.isdigit() & df_poblacion["MES_NUM"].notna()
    df_poblacion["FECHA"] = pd.NaT
    if valid_rows.any():
        df_poblacion.loc[valid_rows, "FECHA"] = pd.to_datetime(
            df_poblacion.loc[valid_rows, "ANO"].astype(int).astype(str) + "-" +
            df_poblacion.loc[valid_rows, "MES_NUM"].astype(int).astype(str).str.zfill(2) + "-01",
            errors="coerce"
        )
    df_poblacion = df_poblacion.drop(columns=["MES_STR", "MES_NUM"], errors="ignore")

    # ---------- Merge con geo (si existe) ----------
    if not df_geo.empty:
        dane_col_geo = None
        for c in df_geo.columns:
            if c.strip().upper() == "DANE":
                dane_col_geo = c
                break
        if dane_col_geo is None and "DANE" not in df_geo.columns:
            dane_col_geo = df_geo.columns[0]

        df_poblacion["DANE_STR"] = df_poblacion["DANE"].astype(str).str.zfill(5)
        df_geo["DANE_STR"] = df_geo[dane_col_geo].astype(str).str.zfill(5)

        geo_candidates = ["REGIÓN", "MUNICIPIO", "REGIONAL", "ZONAL", "PROVINCIA",
                          "DEPARTAMENTO", "CATEGORIA_DEPARTAMENTO", "CATEGORIA_MUNICIPIO",
                          "DESCRIPCIÓN_ZONA", "SUBREGIÓN", "DESCRIPCION_ZONA"]

        geo_cols_present = []
        for col in df_geo.columns:
            for candidate in geo_candidates:
                if candidate.replace("_", "") in col.replace("_", ""):
                    geo_cols_present.append(col)
                    break
        geo_cols_present = list(dict.fromkeys(geo_cols_present))

        try:
            df_geo_unique = df_geo[["DANE_STR"] + geo_cols_present].drop_duplicates(subset=["DANE_STR"]).copy()
            df_poblacion = df_poblacion.drop(columns=[c for c in geo_cols_present if c in df_poblacion.columns], errors="ignore")
            df_poblacion = df_poblacion.merge(df_geo_unique, how="left", on="DANE_STR")
            for c in geo_cols_present:
                if c in df_poblacion.columns:
                    df_poblacion[c] = df_poblacion[c].fillna("N/A")
        except Exception:
            st.warning("No se pudo hacer el merge territorial completo; la app sigue funcionando con filtros limitados.")
        finally:
            df_poblacion = df_poblacion.drop(columns=["DANE_STR"], errors="ignore")
    else:
        st.info("Archivo de territorialidad no cargado. Los filtros geográficos estarán limitados.")


    # ---------- Validaciones mínimas y Pre-procesamiento (Componentes) ----------
    if not df_componentes.empty:
        # Columnas de montos
        comp_monto_cols = ["PRESUPUESTO", "EJECUTADO"] 

        for c in comp_monto_cols:
            if c not in df_componentes.columns:
                df_componentes[c] = 0
            
            # Convertir a numérica y rellenar NaNs con 0
            df_componentes[c] = pd.to_numeric(df_componentes[c], errors="coerce").fillna(0)

        # Columna de Ejecución, si existe en el DF original (el nombre fue estandarizado en normalize_columns)
        if "PORCENTAJE_EJECUCION" not in df_componentes.columns:
             # Si no está, se crea con 0
            df_componentes["PORCENTAJE_EJECUCION"] = 0
        
        # Columna de Diferencia, si existe en el DF original (NO es necesaria, se recalcula)
        if "DIFERENCIA" in df_componentes.columns:
            df_componentes = df_componentes.drop(columns=["DIFERENCIA"])


        comp_text_cols = ["ANO", "MES", "REGIMEN", "CONCEPTO"]
        for c in comp_text_cols:
             if c in df_componentes.columns:
                df_componentes[c] = df_componentes[c].astype(str).str.upper().str.strip()
    else:
        st.info("Archivo de Componentes no cargado o vacío.")

    # =========================================================================
    # --- FILTROS
    # =========================================================================

    # ---------- FILTROS (comunes) ----------
    with st.expander("Filtros de Tiempo y Régimen", expanded=True):
        c1, c2, c3, c4 = st.columns([1,1,1,1])

        # Año
        anos = sorted([a for a in df_poblacion["ANO"].dropna().unique().tolist() if a != "N/A"])
        selected_ano = c1.selectbox("Año", options=anos, index=len(anos)-1 if anos else 0)

        # Mes
        meses = [m for m in df_poblacion["MES"].dropna().unique().tolist() if m != "N/A"]
        meses_opts = ["Todos"] + meses
        selected_mes = c2.selectbox("Mes", options=meses_opts, index=0)

        # Régimen
        regimenes = [r for r in df_poblacion["REGIMEN"].dropna().unique().tolist() if r != "N/A"]
        regimenes_opts = ["Todos"] + regimenes
        selected_regimen = c3.selectbox("Régimen", options=regimenes_opts, index=0)


        # reset button
        if c4.button("Restablecer filtros"):
            st.experimental_rerun()

    # ---------- Filtros geográficos colapsables ----------
    with st.expander("Filtros de Georreferenciación", expanded=False):
        def get_select_options(df, col):
            """Obtiene opciones únicas, robustamente, si la columna existe."""
            if col not in df.columns: # <--- Control de existencia de columna
                return ["Todos"]
                
            opts = sorted([v for v in df.get(col, pd.Series()).dropna().unique() if v != "N/A"])
            return ["Todos"] + opts

        # 1. Región / Depto / Municipio (dependientes)
        sel_region = st.selectbox("Región", options=get_select_options(df_poblacion, "REGIÓN"), index=0)

        # Lógica de filtrado dependiente robusta: solo filtra si la columna existe
        df_dept = df_poblacion.copy()
        if sel_region != "Todos" and "REGIÓN" in df_poblacion.columns:
            df_dept = df_poblacion[df_poblacion["REGIÓN"] == sel_region].copy()
            
        sel_depto = st.selectbox("Departamento", options=get_select_options(df_dept, "DEPARTAMENTO"), index=0)

        df_mun = df_dept.copy()
        if sel_depto != "Todos" and "DEPARTAMENTO" in df_dept.columns:
            df_mun = df_dept[df_dept["DEPARTAMENTO"] == sel_depto].copy()

        sel_mun = st.selectbox("Municipio", options=get_select_options(df_mun, "MUNICIPIO"), index=0)

        st.markdown("---")

        # 2. Regional / Zonal / Provincia
        cA, cB, cC = st.columns(3)
        sel_regional = cA.selectbox("Regional", options=get_select_options(df_poblacion, "REGIONAL"), index=0)
        sel_zonal = cB.selectbox("Zonal", options=get_select_options(df_poblacion, "ZONAL"), index=0)
        sel_provincia = cC.selectbox("Provincia", options=get_select_options(df_poblacion, "PROVINCIA"), index=0)

        st.markdown("---")

        # 3. Categorías y Descripción
        cD, cE, cF = st.columns(3)
        sel_cat_depto = cD.selectbox("Categoría Departamento", options=get_select_options(df_poblacion, "CATEGORIA_DEPARTAMENTO"), index=0)
        sel_cat_mun = cE.selectbox("Categoría Municipio", options=get_select_options(df_poblacion, "CATEGORIA_MUNICIPIO"), index=0)
        sel_desc_zona = cF.selectbox("Descripción Zona", options=get_select_options(df_poblacion, "DESCRIPCIÓN_ZONA"), index=0)

        sel_subregion = st.selectbox("Subregión", options=get_select_options(df_poblacion, "SUBREGIÓN"), index=0)


    # =========================================================================
    # --- APLICAR FILTROS
    # =========================================================================

    df_filtrado_full = df_poblacion.copy()
    df_filtrado_comp = df_componentes.copy() 
    df_filtrado_for_trend = df_poblacion.copy()

    def aplicar_filtro_select(df, col, valor_seleccionado):
        """Aplica filtro de columna de forma segura (sin KeyError) y evita SettingWithCopyWarning."""
        if col not in df.columns or valor_seleccionado == "Todos":
            return df
        
        valor_seleccionado_str = str(valor_seleccionado).upper().strip()
        
        # *** CORRECCIÓN FUTURE WARNING ***
        # Convertir a string antes de hacer .str.upper() para evitar SettingWithCopyWarning 
        # y dtype incompatible cuando la columna original era numérica (como ANO).
        # Uso de .loc para asegurar la operación en la copia.
        df.loc[:, col] = df[col].astype(str).str.upper().str.strip() 
        
        # Aplicar el filtro
        return df[df[col] == valor_seleccionado_str]


    # FIX CRÍTICO: Convertir el año seleccionado a string para compatibilidad con la columna de componentes
    selected_ano_str = str(selected_ano) 

    # Filtro de Año
    df_filtrado_full = aplicar_filtro_select(df_filtrado_full, "ANO", selected_ano_str)
    df_filtrado_for_trend = aplicar_filtro_select(df_filtrado_for_trend, "ANO", selected_ano_str) # Filtro de Año aplicado a la data de tendencia
    
    # Aplicar filtro de Año a df_componentes
    if not df_filtrado_comp.empty and "ANO" in df_filtrado_comp.columns:
        df_filtrado_comp = aplicar_filtro_select(df_filtrado_comp, "ANO", selected_ano_str)
        

    # Filtros de Mes y Régimen
    # NOTA: El filtro de MES se aplica SOLO a df_filtrado (que será kpis), NO a df_filtrado_for_trend (que será chart).
    df_filtrado = aplicar_filtro_select(df_filtrado_full, "MES", selected_mes) 
    if not df_filtrado_comp.empty and "MES" in df_filtrado_comp.columns:
        df_filtrado_comp = aplicar_filtro_select(df_filtrado_comp, "MES", selected_mes)

    df_filtrado = aplicar_filtro_select(df_filtrado, "REGIMEN", selected_regimen)
    df_filtrado_for_trend = aplicar_filtro_select(df_filtrado_for_trend, "REGIMEN", selected_regimen) # Filtro de Régimen aplicado a la data de tendencia
    if not df_filtrado_comp.empty and "REGIMEN" in df_filtrado_comp.columns:
        df_filtrado_comp = aplicar_filtro_select(df_filtrado_comp, "REGIMEN", selected_regimen)
    
    # Filtros Geográficos
    geo_filters = [
        ("REGIÓN", sel_region), ("DEPARTAMENTO", sel_depto), ("MUNICIPIO", sel_mun),
        ("REGIONAL", sel_regional), ("ZONAL", sel_zonal), ("PROVINCIA", sel_provincia),
        ("CATEGORIA_DEPARTAMENTO", sel_cat_depto), ("CATEGORIA_MUNICIPIO", sel_cat_mun),
        ("DESCRIPCIÓN_ZONA", sel_desc_zona), ("SUBREGIÓN", sel_subregion)
    ]

    # Aplicamos los filtros geográficos de forma segura
    for col, sel_val in geo_filters:
        # aplicar_filtro_select maneja la no existencia de columna y la selección "Todos"
        df_filtrado = aplicar_filtro_select(df_filtrado, col, sel_val)
        df_filtrado_for_trend = aplicar_filtro_select(df_filtrado_for_trend, col, sel_val)
    
    df_filtrado_kpis = df_filtrado
    df_filtrado_componentes = df_filtrado_comp


    # ---------- INTERFAZ: pestañas (después de los filtros) ----------
    tab_kpis, tab_detalle, tab_graficos, tab_componentes = st.tabs(["KPIs", "Detalle", "Gráficos", "Componentes"])


    # ---------- Si no hay datos (Global) ----------
    data_kpis_empty = df_filtrado_kpis.empty or (df_filtrado_kpis["TOTAL_PRESUPUESTO"].sum() == 0 and df_filtrado_kpis["TOTAL_EJECUTADO"].sum() == 0)
    data_comp_empty = df_filtrado_componentes.empty or (df_filtrado_componentes["PRESUPUESTO"].sum() == 0 and df_filtrado_componentes["EJECUTADO"].sum() == 0)

    if data_kpis_empty and data_comp_empty:
        with tab_kpis:
            st.error("No hay datos disponibles con los filtros seleccionados.")
        with tab_componentes:
            st.write("No hay datos de Componentes para mostrar.")
        return
    
    if data_kpis_empty and not data_comp_empty:
         with tab_kpis:
             st.warning("No hay datos de Ejecución VPO para los filtros seleccionados, solo de Componentes.")


    # ---------- KPIs (tab) --- Mantenido Horizontal ----------
    with tab_kpis:
        if not data_kpis_empty:
            st.markdown("### Indicadores (KPIs)")

            # --- 1. Ejecución Total (Horizontal) ---
            st.subheader("Ejecución Total")

            total_presupuesto = df_filtrado_kpis.get("TOTAL_PRESUPUESTO", pd.Series(dtype=float)).sum()
            total_ejecutado = df_filtrado_kpis.get("TOTAL_EJECUTADO", pd.Series(dtype=float)).sum()
            diferencia_total = total_ejecutado - total_presupuesto
            porcentaje_ejecucion_total = (total_ejecutado / total_presupuesto) * 100 if total_presupuesto != 0 else 0

            kpi_cols = st.columns(4)

            kpi_cols[0].metric("Presupuesto Total", fmt_money(total_presupuesto))
            kpi_cols[1].metric("Ejecutado Total", fmt_money(total_ejecutado))

            delta_sign = "" if diferencia_total >= 0 else ""
            delta_color = "normal" if diferencia_total >= 0 else "inverse"
            kpi_cols[2].metric("Diferencia (Ejecutado - Presupuesto)", fmt_money(abs(diferencia_total)),
                                delta=f"{delta_sign}{fmt_money(diferencia_total)}",
                                delta_color=delta_color)

            pct_color = "#D8180A" if porcentaje_ejecucion_total <= 90 else "#058a2d" # Menos del 90% en rojo
            kpi_cols[3].markdown(
                f"""
                <div style="background-color: #f0f2f6; padding: 10px; border-radius: 10px;">
                    <p style="font-size: 0.8rem; color: #555; margin-bottom: 0;">% Ejecución Global</p>
                    <p style="font-size: 1.2rem; color: {pct_color}; font-weight: bold; margin-top: 0;">
                        {fmt_pct(porcentaje_ejecucion_total)}
                    </p>
                </div>
                """, unsafe_allow_html=True
            )

            st.markdown("---")

            # --- 2. Ejecución por Subcuenta (Horizontal) ---
            st.subheader("Ejecución por Subcuenta")
            rubros = ["UPC_LMA", "PYP", "PROVISION"]

            header_cols = st.columns([2, 1.5, 1.5, 1.5, 1.5])
            header_cols[0].markdown("**Subcuenta**")
            header_cols[1].markdown("**Presupuesto**")
            header_cols[2].markdown("**Ejecutado**")
            header_cols[3].markdown("**Diferencia**")
            header_cols[4].markdown("**% Ejecución**")

            st.markdown("---")

            for r in rubros:
                p_col = f"PRESUPUESTO_{r}"
                e_col = f"EJECUTADO_{r}"
                P = df_filtrado_kpis.get(p_col, pd.Series(dtype=float)).sum()
                E = df_filtrado_kpis.get(e_col, pd.Series(dtype=float)).sum()
                D = E - P
                Pct = (E / P) * 100 if P != 0 else 0

                data_cols = st.columns([2, 1.5, 1.5, 1.5, 1.5])
                data_cols[0].markdown(f"**{r.replace('_', ' ')}**")
                data_cols[1].markdown(fmt_money(P))
                data_cols[2].markdown(fmt_money(E))
                
                diff_color = "#15803d" if D >= 0 else "#dc2626"
                data_cols[3].markdown(f"<span style='color:{diff_color};'>{fmt_money(D)}</span>", unsafe_allow_html=True)
                
                pct_color = "#dc2626" if Pct <= 90 else "#15803d" 
                data_cols[4].markdown(f"<span style='color:{pct_color}; font-weight:bold;'>{fmt_pct(Pct)}</span>", unsafe_allow_html=True)
                st.markdown("---")
        else:
            st.info("No hay datos de Indicadores (KPIs) para mostrar con los filtros seleccionados.")


    # ---------- Detalle (tab) ----------
    with tab_detalle:
        if not data_kpis_empty:
            st.markdown("### Tablas de Ejecución")

            st.markdown("#### Ejecución por Mes")
            # Usamos df_filtrado_for_trend aquí también para la tabla de detalle por Mes
            table_mes = create_kpi_table(df_filtrado_for_trend, "MES")
            if table_mes:
                df_display, df_export = table_mes
                # CORRECCIÓN DE WARNING: use_container_width=True -> width='stretch'
                st.dataframe(df_display, width='stretch', hide_index=True) 
                csv_mes = df_export.to_csv(index=False).encode("utf-8")
                st.download_button("Descargar por Mes (CSV)", data=csv_mes, file_name="vpo_mes_kpis.csv", mime="text/csv")
            else:
                st.info("No hay datos por Mes disponibles para esta agregación con los filtros aplicados.")

            st.markdown("---")

            st.markdown("#### Ejecución por Régimen")
            table_regimen = create_kpi_table(df_filtrado_kpis, "REGIMEN")
            if table_regimen:
                df_display, df_export = table_regimen
                # CORRECCIÓN DE WARNING: use_container_width=True -> width='stretch'
                st.dataframe(df_display, width='stretch', hide_index=True)
                csv_regimen = df_export.to_csv(index=False).encode("utf-8")
                st.download_button("Descargar por Régimen (CSV)", data=csv_regimen, file_name="vpo_regimen_kpis.csv", mime="text/csv")
            else:
                st.info("No hay datos de Régimen disponibles para esta agregación.")

            st.markdown("---")
            
            st.markdown("#### Ejecución por Regional")
            table_regional = create_kpi_table(df_filtrado_kpis, "REGIONAL")
            if table_regional:
                df_display, df_export = table_regional
                # CORRECCIÓN DE WARNING: use_container_width=True -> width='stretch'
                st.dataframe(df_display, width='stretch', hide_index=True)
                csv_regional = df_export.to_csv(index=False).encode("utf-8")
                st.download_button("Descargar por Regional (CSV)", data=csv_regional, file_name="vpo_regional_kpis.csv", mime="text/csv")
            else:
                st.info("No hay datos de Regional disponibles para esta agregación.")
            
            st.markdown("---")

            st.markdown("#### Ejecución por Región")
            table_region = create_kpi_table(df_filtrado_kpis, "REGIÓN")
            if table_region:
                df_display, df_export = table_region
                # CORRECCIÓN DE WARNING: use_container_width=True -> width='stretch'
                st.dataframe(df_display, width='stretch', hide_index=True)
                csv_region = df_export.to_csv(index=False).encode("utf-8")
                st.download_button("Descargar por Región (CSV)", data=csv_region, file_name="vpo_region_kpis.csv", mime="text/csv")

                with st.expander("Ver Detalle Jerárquico (Subregión y Zonal)"):
                    st.markdown("##### Detalle por Subregión")
                    table_subregion = create_kpi_table(df_filtrado_kpis, "SUBREGIÓN")
                    if table_subregion:
                        df_sub_display, df_sub_export = table_subregion
                        # CORRECCIÓN DE WARNING: use_container_width=True -> width='stretch'
                        st.dataframe(df_sub_display, width='stretch', hide_index=True)
                        csv_subregion = df_sub_export.to_csv(index=False).encode("utf-8")
                        st.download_button("Descargar Detalle por Subregión (CSV)", data=csv_subregion, file_name="vpo_subregion_kpis.csv", mime="text/csv")
                    else:
                        st.info("No hay datos de Subregión disponibles para este filtro.")

                    st.markdown("---")
                    
                    st.markdown("##### Detalle por Zonal")
                    table_zonal = create_kpi_table(df_filtrado_kpis, "ZONAL")
                    if table_zonal:
                        df_zonal_display, df_zonal_export = table_zonal
                        # CORRECCIÓN DE WARNING: use_container_width=True -> width='stretch'
                        st.dataframe(df_zonal_display, width='stretch', hide_index=True)
                        csv_zonal = df_zonal_export.to_csv(index=False).encode("utf-8")
                        st.download_button("Descargar Detalle por Zonal (CSV)", data=csv_zonal, file_name="vpo_zonal_kpis.csv", mime="text/csv")
                    else:
                        st.info("No hay datos de Zonal disponibles para este filtro.")
            else:
                st.info("No hay datos de Región disponibles para esta agregación.")
        else:
            st.info("No hay datos de Detalle de Ejecución VPO para mostrar con los filtros seleccionados.")

    # =========================================================================
    # --- PESTAÑA: GRÁFICOS (Implementación con Plotly) ---
    # =========================================================================
    with tab_graficos:
        st.markdown("### Ejecución Mensual")

        if not data_kpis_empty:
            
            st.markdown("#### Presupuesto vs. Ejecutado por Mes con % de Ejecución")

            # 1. Agregación de datos por MES
            df_chart = df_filtrado_for_trend.groupby("MES").agg(
                PRESUPUESTO=("TOTAL_PRESUPUESTO", "sum"),
                EJECUTADO=("TOTAL_EJECUTADO", "sum")
            ).reset_index()

            # 2. Cálculo de métricas adicionales
            df_chart['PORCENTAJE_EJECUCION'] = (df_chart['EJECUTADO'] / df_chart['PRESUPUESTO']) * 100
            # Preparamos la etiqueta de texto 
            df_chart['PCT_LABEL'] = df_chart['PORCENTAJE_EJECUCION'].apply(
                lambda x: f"{x:,.1f}%" if pd.notna(x) and x > 0 else "" 
            )
            
            # 3. Solo incluir filas donde el presupuesto sea > 0
            df_chart = df_chart[df_chart['PRESUPUESTO'] > 0].copy()

            if not df_chart.empty and "MES" in df_chart.columns:
                # 4. Preparación para Plotly: Ordenar por MES
                mapeo_meses = {
                    'ENE': 1, 'FEB': 2, 'MAR': 3, 'ABR': 4, 'MAY': 5, 'JUN': 6,
                    'JUL': 7, 'AGO': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DIC': 12
                }
                
                df_chart["MES_ORDER"] = df_chart["MES"].astype(str).str.upper().str.strip().map(mapeo_meses)
                df_chart = df_chart.dropna(subset=["MES_ORDER"]).sort_values("MES_ORDER").copy()
                
                # --- Implementación con Plotly ---
                
                # Creamos la figura, añadiendo las dos series de barras
                fig = go.Figure(data=[
                    go.Bar(
                        name='PRESUPUESTO', 
                        x=df_chart['MES'], 
                        y=df_chart['PRESUPUESTO'],
                        marker_color='#a1a1aa', # Color gris/claro para Presupuesto
                        hovertemplate='Mes: %{x}<br>Presupuesto: %{y:$,.0f}<extra></extra>'
                    ),
                    go.Bar(
                        name='EJECUTADO', 
                        x=df_chart['MES'], 
                        y=df_chart['EJECUTADO'],
                        marker_color='#4ade80', # Color verde para Ejecutado
                        hovertemplate='Mes: %{x}<br>Ejecutado: %{y:$,.0f}<extra></extra>'
                    )
                ])
                
                # Añadir las etiquetas de porcentaje
                for i, row in df_chart.iterrows():
                    # Solo añadimos si hay una etiqueta válida
                    if row['PCT_LABEL']:
                        fig.add_annotation(
                            x=row['MES'], 
                            y=row['EJECUTADO'], # Posiciona la etiqueta sobre la barra Ejecutado
                            text=row['PCT_LABEL'],
                            showarrow=False,
                            yshift=10, # Desplazamiento vertical para que no toque la barra
                            font=dict(color="black", size=10)
                        )

                fig.update_layout(
                    barmode='group', # Esto es CLAVE: agrupa las barras por Mes
                    title='Presupuesto vs. Ejecutado por Mes',
                    xaxis_title='Mes',
                    yaxis_title='Valor ($)',
                    yaxis_tickformat='$,.0f', # Formato de moneda
                    legend_title_text='Tipo de Monto',
                    # Aseguramos que el eje Y comience en 0 para comparaciones de barras
                    yaxis=dict(rangemode='tozero') 
                )
                
                # Usamos st.plotly_chart para renderizar
                st.plotly_chart(fig, use_container_width=True)
                
            else:
                st.info("No hay datos de ejecución por mes disponibles (Presupuesto > $0) para generar el gráfico.")
        else:
             st.info("No hay datos de Gráficos de Ejecución VPO para mostrar con los filtros seleccionados.")

    
    # =========================================================================
    # --- PESTAÑA: COMPONENTES ---
    # =========================================================================
    with tab_componentes:
        st.markdown("### Ejecución por Componente")
        st.markdown("---")

        if data_comp_empty:
            st.warning("No hay datos de Componentes disponibles con los filtros de tiempo y régimen seleccionados.")
        else:
            # Llamada a la función de componentes
            table_componente = create_componente_table(df_filtrado_componentes)

            if table_componente:
                df_display, df_export = table_componente

                st.dataframe(df_display, width='stretch', hide_index=True)

                csv_componente = df_export.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Descargar por Componente (CSV)",
                    data=csv_componente,
                    file_name="vpo_componente_kpis.csv",
                    mime="text/csv"
                )
            else:
                 st.info("No hay datos de Componentes para mostrar después del procesamiento.")

if __name__ == "__main__":
    mostrar_ingreso()