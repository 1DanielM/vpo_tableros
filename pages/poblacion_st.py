import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go 
import numpy as np
import os
from pathlib import Path

# ==============================================================================
# 1. CONFIGURACIÓN Y ESTILOS
# ==============================================================================

# --- 1.1. Mapa de Meses para Ordenamiento Cronológico ---
MONTH_ORDER = {
    'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4,
    'MAYO': 5, 'JUNIO': 6, 'JULIO': 7, 'AGOSTO': 8,
    'SEPTIEMBRE': 9, 'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12
}

# --- 1.2. Estilos CSS Personalizados ---
st.markdown("""
    <style>
    /* Estilo para los KPI cards: TAMAÑO DE CAJA Y LETRA REDUCIDOS */
    .kpi-card {
        background-color: #4A90E2;
        color: white;
        padding: 15px;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin-bottom: 15px;
        height: 100%;
    }
    .kpi-title {
        font-size: 1rem;
        margin-bottom: 5px;
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: bold;
    }
    /* Estilo para alinear el botón de restablecer (si se añade) */
    .stButton>button {
        width: 100%;
        margin-top: 1.7rem;
    }
    /* Estilo para los títulos de los grupos de KPI por Régimen */
    .regimen-header {
        font-size: 1.3rem;
        font-weight: bold;
        color: #1E3A8A;
        padding: 10px 0 5px 0;
        border-bottom: 2px solid #E0E0E0;
        margin-top: 20px;
    }
    </style>
""", unsafe_allow_html=True)


# ==============================================================================
# 2. CONFIGURACIÓN DE RUTAS Y DATOS 
# PARA LA FUSIÓN
# ==============================================================================

# --- Rutas de Archivos (Usando la ruta absoluta proporcionada) ---
# Se asume que esta ruta es correcta en el entorno del usuario
BASE_PATH = r"C:\Users\dmendozad\Documents\Py\DATOS"
FILE_POBLACION = "informes_vpo.xlsx"
FILE_TERRITORIALIDAD = "territorialidad_por_municipio_v5.xlsx"

# --- Definición de Campos y Hojas ---
SHEET_POBLACION = "poblacion"
FIELDS_POBLACION = ['ANO', 'MES', 'REGIMEN', 'DANE', 'PRESUPUESTO', 'POBLACION_BDUA', 'POBLACION_INTEGRAL', 'POBLACION_PAIS']

SHEET_TERRITORIALIDAD = "cobertura_eps"
FIELDS_TERRITORIALIDAD = ['DANE', 'MUNICIPIO', 'REGIONAL', 'ZONAL', 'PROVINCIA', 'DEPARTAMENTO', 'CATEGORIA DEPARTAMENTO', 'CATEGORIA MUNICIPIO', 'DESCRIPCIÓN ZONA', 'REGIÓN', 'SUBREGIÓN', 'CATEGORIA REGION']

# Campos requeridos por el tablero después de la fusión y que tienen espacios
REQUIRED_COLS_DASHBOARD = {
    'POBLACION_PAIS': 'POBLACION PAIS',
    'POBLACION_INTEGRAL': 'POBLACION INTEGRAL' 
}


@st.cache_data
def load_data():
    """
    Carga, fusiona y pre-procesa los datos de población y territorialidad.
    """
    try:
        # CORRECCIÓN DE SINTAXIS: Uso correcto de os.path.join para rutas
        path_poblacion = os.path.join(BASE_PATH, FILE_POBLACION)
        df_poblacion = pd.read_excel(
            path_poblacion,
            sheet_name=SHEET_POBLACION,
            usecols=FIELDS_POBLACION
        )

        path_territorialidad = os.path.join(BASE_PATH, FILE_TERRITORIALIDAD)
        df_territorialidad = pd.read_excel(
            path_territorialidad,
            sheet_name=SHEET_TERRITORIALIDAD,
            usecols=FIELDS_TERRITORIALIDAD
        )

        df_poblacion['DANE'] = df_poblacion['DANE'].astype(str)
        df_territorialidad['DANE'] = df_territorialidad['DANE'].astype(str)

        df_merged = pd.merge(
            df_poblacion,
            df_territorialidad,
            on='DANE',
            how='inner'
        )

        # Aplicamos renombrado antes de la conversión general a mayúsculas
        df_merged.rename(columns=REQUIRED_COLS_DASHBOARD, inplace=True)

        # Convertir a mayúsculas las columnas categóricas, incluyendo las renombradas
        cols_to_clean = ['REGIÓN', 'REGIONAL', 'SUBREGIÓN', 'DEPARTAMENTO', 'MUNICIPIO', 'REGIMEN', 'MES', 'ZONAL']
        for col in cols_to_clean:
            # CORRECCIÓN DE SINTAXIS: Usar el nombre de columna en minúsculas para buscar en df_merged.columns
            # Se ha simplificado esta lógica asumiendo que ya tienen nombres correctos
            if col.upper() in df_merged.columns:
                df_merged[col.upper()] = df_merged[col.upper()].astype(str).str.upper().fillna('SIN INFORMACIÓN')
            elif col in df_merged.columns:
                df_merged[col] = df_merged[col].astype(str).str.upper().fillna('SIN INFORMACIÓN')
        
        # Convertir TODAS las columnas a MAYÚSCULAS después de la limpieza y renombrado
        df_merged.columns = [col.upper() for col in df_merged.columns]

        if 'ANO' in df_merged.columns:
            df_merged['ANO'] = df_merged['ANO'].astype(str)
        if 'MES' in df_merged.columns:
            df_merged['MES'] = df_merged['MES'].astype(str)

        return df_merged

    except FileNotFoundError as e:
        st.error(f"Error: Archivo de datos no encontrado. Verifique la ruta {BASE_PATH} y los nombres de archivos. Detalles: {e}")
        return None
    except KeyError as e:
        st.error(f"Error: Una columna especificada no existe en uno de los archivos. Verifique que sus nombres de columna sean correctos. Detalles: {e}")
        return None
    except Exception as e:
        st.error(f"Error general al cargar y fusionar datos: {e}")
        return None


def create_kpi_card(title, value, format_str="{:,.0f}"):
    """Genera una tarjeta KPI con el formato HTML/CSS."""
    if title.startswith("% Participación"):
        format_str = "{:.2f}%"

    if pd.isna(value) or value is None:
        formatted_value = "N/A"
    else:
        try:
            formatted_value = format_str.format(value)
        except ValueError:
            formatted_value = str(value)

    html_card = f"""
    <div class="kpi-card">
        <div class="kpi-title">{title}</div>
        <div class="kpi-value">{formatted_value}</div>
    </div>
    """
    st.markdown(html_card, unsafe_allow_html=True)


# ==============================================================================
# 3. LÓGICA PRINCIPAL DEL TABLERO
# ==============================================================================

def poblacion_st():

    st.title("Tablero de seguimiento de Poblacion - BDUA")
    st.markdown("---")

    df = load_data()

    if df is None:
        return

    df_temp = df.copy() # DataFrame para filtros de tabla y KPI

    # ======================================================================
    # 3.1. SECCIÓN DE FILTROS
    # ======================================================================
    
    # --- 3.1.1. Filtros de Tiempo y Régimen ---
    st.subheader("Filtros de Tiempo y Régimen")
    with st.container(border=True):
        # CORRECCIÓN DE SINTAXIS: Se elimina la coma final extra en st.columns
        col_a, col_m, col_r, col_reset = st.columns([1, 1, 1, 0.5])
        
        # Guardar el estado de los filtros y aplicar AJUSTE 1: Año por defecto 2025
        if "filtro_ano" not in st.session_state:
            st.session_state["filtro_ano"] = '2025' 
        if "filtro_mes" not in st.session_state:
            st.session_state["filtro_mes"] = 'TODOS'
        if "filtro_regimen" not in st.session_state:
            st.session_state["filtro_regimen"] = 'TODOS'

        with col_a:
            available_anos = sorted(df_temp['ANO'].unique(), reverse=True)
            options_anos = ['TODOS'] + available_anos
            default_year = '2025'
            # Determina el índice a usar
            default_index = options_anos.index(st.session_state["filtro_ano"]) if st.session_state["filtro_ano"] in options_anos else options_anos.index(default_year) if default_year in options_anos else 0
            
            selected_ano = st.selectbox("Año", options_anos, index=default_index, key="filtro_ano_select")
        
        # Aplicación del filtro de Año
        if selected_ano != 'TODOS':
            df_temp = df_temp[df_temp['ANO'] == selected_ano]
        st.session_state["filtro_ano"] = selected_ano


        with col_m:
            available_meses = sorted(df_temp['MES'].unique(), key=lambda x: MONTH_ORDER.get(x, 99))
            options_meses = ['TODOS'] + available_meses
            
            # Ajuste dinámico del mes preseleccionado si ya no existe en el nuevo Año
            if st.session_state["filtro_mes"] not in options_meses and available_meses:
                 st.session_state["filtro_mes"] = available_meses[-1]
            elif not available_meses:
                 st.session_state["filtro_mes"] = 'TODOS'
            
            # Índice para la selección
            current_month_index = options_meses.index(st.session_state["filtro_mes"]) if st.session_state["filtro_mes"] in options_meses else 0
            
            selected_mes = st.selectbox("Mes", options_meses, index=current_month_index, key="filtro_mes_select")

        # Aplicación del filtro de Mes (para KPIs, Tablas Detalle excepto la de Mes, y Gráficos)
        if selected_mes != 'TODOS':
            df_temp = df_temp[df_temp['MES'] == selected_mes]
        st.session_state["filtro_mes"] = selected_mes


        with col_r:
            available_regimenes = sorted(df_temp['REGIMEN'].unique())
            options_regimen = ['TODOS'] + available_regimenes
            current_regimen_index = options_regimen.index(st.session_state["filtro_regimen"]) if st.session_state["filtro_regimen"] in options_regimen else 0
            selected_regimen = st.selectbox("Régimen", options_regimen, index=current_regimen_index, key="filtro_regimen_select")
        
        # Aplicación del filtro de Régimen
        if selected_regimen != 'TODOS':
            df_temp = df_temp[df_temp['REGIMEN'] == selected_regimen]
        st.session_state["filtro_regimen"] = selected_regimen


        with col_reset:
            # CORRECCIÓN DE SINTAXIS: Uso de un solo bloque de código para limpiar estados
            st.markdown("<div style='height:1.7rem;'></div>", unsafe_allow_html=True)
            if st.button("Restablecer filtros", type="secondary"):
                 # AJUSTE 1: Restablecer el año a '2025' por defecto
                 st.session_state["filtro_ano"] = '2025' 
                 st.session_state["filtro_mes"] = 'TODOS'
                 st.session_state["filtro_regimen"] = 'TODOS'
              
                 # Limpiar filtros geográficos 
                 for key in ['filtro_region', 'filtro_regional', 'filtro_subregion', 'filtro_departamento', 'filtro_municipio']:
                     if key in st.session_state: 
                         st.session_state.pop(key)
                 st.experimental_rerun()


    # --- 3.1.2. Filtros Geográficos ---
    
    # Mantener el estado de los filtros geográficos
    geo_filter_keys = ['filtro_region', 'filtro_regional', 'filtro_subregion', 'filtro_departamento', 'filtro_municipio']
    for key in geo_filter_keys:
        if key not in st.session_state:
            st.session_state[key] = 'TODOS'


    with st.expander("Filtros de Georreferenciación", expanded=False):
        
        # Region
        col_region, col_regional = st.columns(2)
    
        with col_region:
            available_regiones = sorted(df_temp['REGIÓN'].unique())
            options_regiones = ['TODOS'] + available_regiones
            current_region_index = options_regiones.index(st.session_state["filtro_region"]) if st.session_state["filtro_region"] in options_regiones else 0
            selected_region = st.selectbox("Región", options_regiones, index=current_region_index, key="filtro_region_select")
        
        # Aplicación del filtro de Región
        if selected_region != 'TODOS':
            df_temp = df_temp[df_temp['REGIÓN'] == selected_region]
        st.session_state["filtro_region"] = selected_region

        # Regional
        with col_regional:
            available_regionales = sorted(df_temp['REGIONAL'].unique())
            options_regionales = ['TODOS'] + available_regionales
            current_regional_index = options_regionales.index(st.session_state["filtro_regional"]) if st.session_state["filtro_regional"] in options_regionales else 0
            selected_regional = st.selectbox("Regional", options_regionales, index=current_regional_index, key="filtro_regional_select")
        
        # Aplicación del filtro de Regional
        if selected_regional != 'TODOS':
            df_temp = df_temp[df_temp['REGIONAL'] == selected_regional]
        st.session_state["filtro_regional"] = selected_regional

        # Subregión
        # CORRECCIÓN DE SINTAXIS: Se elimina la coma final extra en st.columns
        col_subreg, col_dep = st.columns(2)
        with col_subreg:
            available_subregiones = sorted(df_temp['SUBREGIÓN'].unique())
            options_subregiones = ['TODOS'] + available_subregiones
            current_subregion_index = options_subregiones.index(st.session_state["filtro_subregion"]) if st.session_state["filtro_subregion"] in options_subregiones else 0
            selected_subregion = st.selectbox("Subregión", options_subregiones, index=current_subregion_index, key="filtro_subregion_select")
        
        # Aplicación del filtro de Subregión
        if selected_subregion != 'TODOS':
            df_temp = df_temp[df_temp['SUBREGIÓN'] == selected_subregion]
        st.session_state["filtro_subregion"] = 'TODOS'


        # Departamento
        with col_dep:
            available_departamentos = sorted(df_temp['DEPARTAMENTO'].unique())
            options_departamentos = ['TODOS'] + available_departamentos
            current_departamento_index = options_departamentos.index(st.session_state["filtro_departamento"]) if st.session_state["filtro_departamento"] in options_departamentos else 0
            selected_departamento = st.selectbox("Departamento", options_departamentos, index=current_departamento_index, key="filtro_departamento_select")
        
        # Aplicación del filtro de Departamento
        if selected_departamento != 'TODOS':
            df_temp = df_temp[df_temp['DEPARTAMENTO'] == selected_departamento]
        st.session_state["filtro_departamento"] = selected_departamento

        # Municipio
        # CORRECCIÓN DE SINTAXIS: Se elimina la coma final extra en st.columns
        col_mun, col_placeholder = st.columns(2)
        with col_mun:
            available_municipios = sorted(df_temp['MUNICIPIO'].unique())
            options_municipios = ['TODOS'] + available_municipios
            current_municipio_index = options_municipios.index(st.session_state["filtro_municipio"]) if st.session_state["filtro_municipio"] in options_municipios else 0
            selected_municipio = st.selectbox("Municipio", options_municipios, index=current_municipio_index, key="filtro_municipio_select")
        
        # Aplicación del filtro de Municipio
        if selected_municipio != 'TODOS':
            df_temp = df_temp[df_temp['MUNICIPIO'] == selected_municipio]
        st.session_state["filtro_municipio"] = selected_municipio

        with col_placeholder:
            st.markdown("<div style='height: 1.7rem;'></div>", unsafe_allow_html=True)


    # DataFrame para cálculos de tablas y KPI (ya filtrado por año, mes, régimen y geografía)
    df_filtered = df_temp

    # === DATAFRAME PARA EL GRÁFICO DE LÍNEA Y LA TABLA MENSUAL ===
    # Usa df original para mantener la vista histórica, pero aplica filtros NO mensuales
    df_chart_data_all_months = df.copy()

    # Aplicar filtros NO mensuales (Año, Régimen y Geográficos) al set de datos para el gráfico de tiempo
    if st.session_state["filtro_ano"] != 'TODOS':
        df_chart_data_all_months = df_chart_data_all_months[df_chart_data_all_months['ANO'] == st.session_state["filtro_ano"]]

    if st.session_state["filtro_regimen"] != 'TODOS':
        df_chart_data_all_months = df_chart_data_all_months[df_chart_data_all_months['REGIMEN'] == st.session_state["filtro_regimen"]]
    
    # Aplicar filtros Geográficos
    geo_filters_active = {
        'REGIÓN': st.session_state["filtro_region"], 'REGIONAL': st.session_state["filtro_regional"], 
        'SUBREGIÓN': st.session_state["filtro_subregion"], 'DEPARTAMENTO': st.session_state["filtro_departamento"], 
        'MUNICIPIO': st.session_state["filtro_municipio"]
    }
    for col, sel_val in geo_filters_active.items():
        if sel_val != 'TODOS' and col in df_chart_data_all_months.columns:
            df_chart_data_all_months = df_chart_data_all_months[df_chart_data_all_months[col] == sel_val]

    # === FIN DEL DATAFRAME PARA EL GRÁFICO Y TABLA MENSUAL ===

    if df_filtered.empty:
        st.warning("No hay datos para los filtros seleccionados.")
        return

    # Usamos POBLACION_BDUA (con guion bajo) y POBLACION PAIS (con espacio)
    total_bdua_filtered = df_filtered['POBLACION_BDUA'].sum()
    total_pais_filtered = df_filtered['POBLACION PAIS'].sum()


    # ======================================================================
    # 3.2. CÁLCULO DE DATAFRAMES RESUMEN
    # ======================================================================
    
    # Nombre de la nueva columna calculada para el cumplimiento (BDUA / Presupuesto)
    NOMBRE_RAZON_INVERSION = '% EJECUCIÓN'
    # Nombre de la nueva columna para Participación País
    COL_PARTICIPACION_PAIS = '% PARTICIPACION PAIS'

    # --- DataFrame por Regional (Vista principal de la tabla original) ---
    df_regional_viz = pd.DataFrame()
    if 'REGIONAL' in df_filtered.columns:
        df_regional_viz = df_filtered.groupby('REGIONAL').agg(
            {'PRESUPUESTO': 'sum', 'POBLACION_BDUA': 'sum', 'POBLACION PAIS': 'sum'}
        ).reset_index()
        
        # CÁLCULO DE % EJECUCIÓN (POBLACION_BDUA / PRESUPUESTO * 100)
        df_regional_viz.loc[:, NOMBRE_RAZON_INVERSION] = np.where(
            df_regional_viz['PRESUPUESTO'] != 0,
            (df_regional_viz['POBLACION_BDUA'] / df_regional_viz['PRESUPUESTO']) * 100,
            0
        )
        # CÁLCULO DE PARTICIPACIÓN PAÍS (POBLACION_BDUA / POBLACION PAIS * 100)
        df_regional_viz.loc[:, COL_PARTICIPACION_PAIS] = np.divide(df_regional_viz['POBLACION_BDUA'], df_regional_viz['POBLACION PAIS']) * 100
        df_regional_viz[COL_PARTICIPACION_PAIS] = df_regional_viz[COL_PARTICIPACION_PAIS].replace([np.inf, -np.inf, np.nan], 0)
        df_regional_viz = df_regional_viz.sort_values(by=COL_PARTICIPACION_PAIS, ascending=False)
        
    # --- DataFrame por Región y Subregión (Para gráficos y expansión en tablas) ---
    df_region_sub = pd.DataFrame()
    if 'REGIÓN' in df_filtered.columns and 'SUBREGIÓN' in df_filtered.columns:
        df_region_sub = df_filtered.groupby(['REGIÓN', 'SUBREGIÓN']).agg(
            {'PRESUPUESTO': 'sum', 'POBLACION_BDUA': 'sum', 'POBLACION PAIS': 'sum'}
        ).reset_index()
        df_region_sub.loc[:, COL_PARTICIPACION_PAIS] = np.divide(df_region_sub['POBLACION_BDUA'], df_region_sub['POBLACION PAIS']) * 100
        df_region_sub[COL_PARTICIPACION_PAIS] = df_region_sub[COL_PARTICIPACION_PAIS].replace([np.inf, -np.inf, np.nan], 0)
   
        # Cálculo de % Ejecución
        df_region_sub.loc[:, NOMBRE_RAZON_INVERSION] = np.where(
            df_region_sub['PRESUPUESTO'] != 0,
            (df_region_sub['POBLACION_BDUA'] / df_region_sub['PRESUPUESTO']) * 100,
            0
        )


    # --- DataFrame por Mes (Resumen por Mes) ---
    df_mes_viz = pd.DataFrame()
    # AJUSTE 2: Usar el DataFrame sin el filtro de mes (df_chart_data_all_months) 
    # para asegurar que todos los meses se vean siempre en esta tabla.
    if 'MES' in df_chart_data_all_months.columns:
        df_mes_viz = df_chart_data_all_months.groupby('MES').agg(
            {'PRESUPUESTO': 'sum', 'POBLACION_BDUA': 'sum', 'POBLACION PAIS': 'sum'}
        ).reset_index()
        df_mes_viz.loc[:, COL_PARTICIPACION_PAIS] = np.divide(df_mes_viz['POBLACION_BDUA'], df_mes_viz['POBLACION PAIS']) * 100
        df_mes_viz[COL_PARTICIPACION_PAIS] = df_mes_viz[COL_PARTICIPACION_PAIS].replace([np.inf, -np.inf, np.nan], 0)
        
        # CÁLCULO DE % EJECUCIÓN (POBLACION_BDUA / PRESUPUESTO)
        df_mes_viz.loc[:, NOMBRE_RAZON_INVERSION] = np.where(
            df_mes_viz['PRESUPUESTO'] != 0,
            (df_mes_viz['POBLACION_BDUA'] / df_mes_viz['PRESUPUESTO']) * 100,
            0
        )
        
        # Aseguramos el orden cronológico
        df_mes_viz['MES_ORDEN'] = df_mes_viz['MES'].map(MONTH_ORDER)
        df_mes_viz = df_mes_viz.sort_values(by='MES_ORDEN').drop(columns=['MES_ORDEN'])


    # --- DataFrame por Régimen (Resumen por Régimen) ---
    df_regimen_table_viz = pd.DataFrame()
    if 'REGIMEN' in df_filtered.columns:
        df_regimen_table_viz = df_filtered.groupby('REGIMEN').agg(
            {'PRESUPUESTO': 'sum', 'POBLACION_BDUA': 'sum', 'POBLACION PAIS': 'sum'}
        ).reset_index()
        df_regimen_table_viz.loc[:, COL_PARTICIPACION_PAIS] = np.divide(df_regimen_table_viz['POBLACION_BDUA'], df_regimen_table_viz['POBLACION PAIS']) * 100
        df_regimen_table_viz[COL_PARTICIPACION_PAIS] = df_regimen_table_viz[COL_PARTICIPACION_PAIS].replace([np.inf, -np.inf, np.nan], 0)
        df_regimen_table_viz = df_regimen_table_viz.sort_values(by='REGIMEN', ascending=True)
        
        # CÁLCULO DE % EJECUCIÓN (POBLACION_BDUA / PRESUPUESTO)
        df_regimen_table_viz.loc[:, NOMBRE_RAZON_INVERSION] = np.where(
            df_regimen_table_viz['PRESUPUESTO'] != 0,
            (df_regimen_table_viz['POBLACION_BDUA'] / df_regimen_table_viz['PRESUPUESTO']) * 100,
            0
        )


    # --- DataFrame por Regional y Zonal (Para expansión en tablas) ---
    df_regional_zonal_viz = pd.DataFrame()
    if 'REGIONAL' in df_filtered.columns and 'ZONAL' in df_filtered.columns:
        df_regional_zonal_viz = df_filtered.groupby(['REGIONAL', 'ZONAL']).agg(
            {'PRESUPUESTO': 'sum', 'POBLACION_BDUA': 'sum', 'POBLACION PAIS': 'sum'}
        ).reset_index()
        df_regional_zonal_viz.loc[:, COL_PARTICIPACION_PAIS] = np.divide(df_regional_zonal_viz['POBLACION_BDUA'], df_regional_zonal_viz['POBLACION PAIS']) * 100
        df_regional_zonal_viz[COL_PARTICIPACION_PAIS] = df_regional_zonal_viz[COL_PARTICIPACION_PAIS].replace([np.inf, -np.inf, np.nan], 0)
        # Cálculo de % Ejecución
        df_regional_zonal_viz.loc[:, NOMBRE_RAZON_INVERSION] = np.where(
             df_regional_zonal_viz['PRESUPUESTO'] != 0,
             (df_regional_zonal_viz['POBLACION_BDUA'] / df_regional_zonal_viz['PRESUPUESTO']) * 100,
             0
         )

    # DataFrame por Régimen (el que alimenta los KPIs y el gráfico de barras)
    df_regimen_viz = pd.DataFrame()
    df_regimen_long = pd.DataFrame()

    if 'REGIMEN' in df_filtered.columns:
        df_regimen_viz = df_filtered.groupby('REGIMEN').agg(
            {'PRESUPUESTO': 'sum', 'POBLACION_BDUA': 'sum', 'POBLACION PAIS': 'sum'}
        ).reset_index()

        df_regimen_viz.loc[:, COL_PARTICIPACION_PAIS] = np.divide(df_regimen_viz['POBLACION_BDUA'], df_regimen_viz['POBLACION PAIS']) * 100
        df_regimen_viz[COL_PARTICIPACION_PAIS] = df_regimen_viz[COL_PARTICIPACION_PAIS].replace([np.inf, -np.inf, np.nan], 0)

        # Cálculos de composición interna (para gráficos)
        if total_bdua_filtered > 0:
            df_regimen_viz.loc[:, '% Participación NEP'] = (df_regimen_viz['POBLACION_BDUA'] / total_bdua_filtered) * 100
        else:
            df_regimen_viz.loc[:, '% Participación NEP'] = 0

        if total_pais_filtered > 0:
            df_regimen_viz.loc[:, '% Participación País'] = (df_regimen_viz['POBLACION PAIS'] / total_pais_filtered) * 100
        else:
            df_regimen_viz.loc[:, '% Participación País'] = 0

        df_regimen_long = df_regimen_viz.melt(
            id_vars=['REGIMEN'],
            value_vars=['% Participación NEP', '% Participación País'],
            var_name='Tipo de Población',
            value_name='Porcentaje'
        )

        df_regimen_viz = df_regimen_viz.sort_values(by='POBLACION_BDUA', ascending=False)


    # Definición de la columna de visualización para Participación País en tablas
    COL_DISPLAY_PARTICIPACION = 'Participación País (%)'
    
    # MODIFICACIÓN DE FORMATO FINAL
    TABLE_FORMAT = {
        'Presupuesto': '{:,.0f}', 
        'Población BDUA': '{:,.0f}', 
        'Población PAIS': '{:,.0f}',
        COL_DISPLAY_PARTICIPACION: '{:.2f}%',
        '% ejecución': '{:.2f}%',
        'Población Integral': '{:,.0f}'
    }

 
    # ======================================================================
    # 3.3. DEFINICIÓN Y CONTENIDO DE PESTAÑAS (Tabs)
    # ======================================================================

    tab_kpis, tab_tables, tab_charts = st.tabs(["📊 KPIs", "📑 Tablas de Detalle", "📈 Gráficos"])

    # --- PESTAÑA 1: KPIs ---
    with tab_kpis:
        st.header("Indicadores Clave de Población")

        # --- Bloque 1: KPIs Globales ---
        st.subheader("Totales Consolidados (Filtros Aplicados)")
        total_bdua = total_bdua_filtered
        total_pais = total_pais_filtered
        if total_pais == 0 or pd.isna(total_pais) or total_pais == 0:
            porc_bdua = 0
        else:
            porc_bdua = (total_bdua / total_pais) * 100

        # CORRECCIÓN DE SINTAXIS: Se elimina la coma final extra en st.columns
        col_kpi1, col_kpi2, col_kpi3, _ = st.columns([1, 1, 1, 1])
        with col_kpi1:
            create_kpi_card("Total Población BDUA", total_bdua)
        with col_kpi2:
            create_kpi_card("Población Total País", total_pais)
        with col_kpi3:
            create_kpi_card("% Participación País", porc_bdua)

        st.markdown("---")

        # --- Bloque 2: KPIs por Régimen ---
        st.header("Indicadores por Régimen")
        if df_regimen_viz.empty:
            st.info("No hay datos por régimen disponibles con los filtros aplicados.")
        else:
            df_regimen_viz_sorted = df_regimen_viz.sort_values(by='REGIMEN', ascending=True)
            for _, row in df_regimen_viz_sorted.iterrows():
                regimen_name = row['REGIMEN']
                reg_bdua = row['POBLACION_BDUA']
                reg_pais = row['POBLACION PAIS']
                reg_porc_pais = row[COL_PARTICIPACION_PAIS]
                
                st.markdown(f"<div class='regimen-header'>{regimen_name}</div>", unsafe_allow_html=True)
                # CORRECCIÓN DE SINTAXIS: Se elimina la coma final extra en st.columns
                col_r_kpi1, col_r_kpi2, col_r_kpi3, _ = st.columns([1, 1, 1, 1])
                with col_r_kpi1:
                    create_kpi_card(f"Población BDUA - {regimen_name}", reg_bdua)
                with col_r_kpi2:
                    create_kpi_card(f"Población País - {regimen_name}", reg_pais)
                with col_r_kpi3:
                    create_kpi_card(f"% Participación País - {regimen_name}", reg_porc_pais)

    # --- PESTAÑA 2: Tablas de Detalle ---
    with tab_tables:
        # --- 1. TABLA POR MES ---
        st.subheader("Resumen por Mes")
        if not df_mes_viz.empty:
            df_mes_table = df_mes_viz.rename(columns={
                'MES': 'Mes',
                'PRESUPUESTO': 'Presupuesto',
                'POBLACION_BDUA': 'Población BDUA',
                'POBLACION PAIS': 'Población PAIS', 
                NOMBRE_RAZON_INVERSION: '% ejecución',
                COL_PARTICIPACION_PAIS: COL_DISPLAY_PARTICIPACION
            })
            st.dataframe(
                df_mes_table[['Mes', 'Presupuesto', 'Población BDUA', '% ejecución', 'Población PAIS', COL_DISPLAY_PARTICIPACION]].style.format(TABLE_FORMAT),
                use_container_width=True,
                hide_index=True 
            )
        else:
            st.info("No hay datos por mes disponibles.")
        st.markdown("---")

        # --- 2. TABLA POR RÉGIMEN ---
        st.subheader("Resumen por Régimen")
        if not df_regimen_table_viz.empty:
            df_regimen_table = df_regimen_table_viz.rename(columns={
                'REGIMEN': 'Régimen',
                'PRESUPUESTO': 'Presupuesto',
                'POBLACION_BDUA': 'Población BDUA',
                'POBLACION PAIS': 'Población PAIS', 
                NOMBRE_RAZON_INVERSION: '% ejecución',
                COL_PARTICIPACION_PAIS: COL_DISPLAY_PARTICIPACION
            })
            st.dataframe(
                df_regimen_table[['Régimen', 'Presupuesto', 'Población BDUA', '% ejecución', 'Población PAIS', COL_DISPLAY_PARTICIPACION]].style.format(TABLE_FORMAT),
                use_container_width=True,
                hide_index=True 
            )
        else:
            st.info("No hay datos por régimen disponibles.")
        st.markdown("---")

        # --- 3. TABLA POR REGIONAL Y REGIONAL/ZONAL ---
        st.subheader("Presupuesto, Población BDUA y Participación País por Regional")
        if not df_regional_viz.empty:
            # Tabla Regional (vista principal)
            df_regional_table = df_regional_viz.rename(columns={
                'REGIONAL': 'Regional',
                'PRESUPUESTO': 'Presupuesto',
                'POBLACION_BDUA': 'Población BDUA',
                'POBLACION PAIS': 'Población PAIS', 
                NOMBRE_RAZON_INVERSION: '% ejecución',
                COL_PARTICIPACION_PAIS: COL_DISPLAY_PARTICIPACION
            })
            st.dataframe(
                df_regional_table[['Regional', 'Presupuesto', 'Población BDUA', '% ejecución', 'Población PAIS', COL_DISPLAY_PARTICIPACION]].style.format(TABLE_FORMAT),
                use_container_width=True,
                hide_index=True 
            )
            # Tabla Regional/Zonal (Expansión)
            if not df_regional_zonal_viz.empty:
                with st.expander("Ver detalle por Zonal"):
                    df_reg_zonal_table = df_regional_zonal_viz.rename(columns={
                        'REGIONAL': 'Regional',
                        'ZONAL': 'Zonal',
                        'PRESUPUESTO': 'Presupuesto',
                        'POBLACION_BDUA': 'Población BDUA',
                        'POBLACION PAIS': 'Población PAIS', 
                        NOMBRE_RAZON_INVERSION: '% ejecución',
                        COL_PARTICIPACION_PAIS: COL_DISPLAY_PARTICIPACION
                    })
                    st.dataframe(
                        df_reg_zonal_table[['Regional', 'Zonal', 'Presupuesto', 'Población BDUA', '% ejecución', 'Población PAIS', COL_DISPLAY_PARTICIPACION]].style.format(TABLE_FORMAT),
                        use_container_width=True,
                        hide_index=True 
                    )
            else:
                st.info("No hay suficiente nivel de detalle regional para mostrar la tabla.")
        st.markdown("---")

        # --- 4. TABLA POR REGIÓN Y REGIÓN/SUBREGIÓN ---
        st.subheader("Resumen por Región")
        if not df_region_sub.empty:
            # Creamos la vista simple por Región
            df_region_viz_simple = df_region_sub.groupby('REGIÓN').agg({
                'PRESUPUESTO': 'sum', 
                'POBLACION_BDUA': 'sum', 
                'POBLACION PAIS': 'sum', 
            }).reset_index()
            # Recalculamos % Ejecución y Participación País a nivel de Región
            df_region_viz_simple.loc[:, NOMBRE_RAZON_INVERSION] = np.where(
                df_region_viz_simple['PRESUPUESTO'] != 0,
                (df_region_viz_simple['POBLACION_BDUA'] / df_region_viz_simple['PRESUPUESTO']) * 100,
                0
            )
            df_region_viz_simple.loc[:, COL_PARTICIPACION_PAIS] = np.divide(df_region_viz_simple['POBLACION_BDUA'], df_region_viz_simple['POBLACION PAIS']) * 100
            df_region_viz_simple[COL_PARTICIPACION_PAIS] = df_region_viz_simple[COL_PARTICIPACION_PAIS].replace([np.inf, -np.inf, np.nan], 0)

            # Ajuste de nombres de columna para la tabla
            df_region_table = df_region_viz_simple.rename(columns={
                'REGIÓN': 'Región',
                'PRESUPUESTO': 'Presupuesto',
                'POBLACION_BDUA': 'Población BDUA',
                'POBLACION PAIS': 'Población PAIS', 
                NOMBRE_RAZON_INVERSION: '% ejecución',
                COL_PARTICIPACION_PAIS: COL_DISPLAY_PARTICIPACION
            })
            st.dataframe(
                df_region_table[['Región', 'Presupuesto', 'Población BDUA', '% ejecución', 'Población PAIS', COL_DISPLAY_PARTICIPACION]].style.format(TABLE_FORMAT),
                use_container_width=True,
                hide_index=True 
            )
            # Tabla Región/Subregión (Expansión)
            if not df_region_sub.empty:
                with st.expander("Ver detalle por Subregión"):
                    df_reg_sub_table = df_region_sub.rename(columns={
                        'REGIÓN': 'Región',
                        'SUBREGIÓN': 'Subregión',
                        'PRESUPUESTO': 'Presupuesto',
                        'POBLACION_BDUA': 'Población BDUA',
                        'POBLACION PAIS': 'Población PAIS', 
                        NOMBRE_RAZON_INVERSION: '% ejecución',
                        COL_PARTICIPACION_PAIS: COL_DISPLAY_PARTICIPACION
                    })
                    st.dataframe(
                        df_reg_sub_table[['Región', 'Subregión', 'Presupuesto', 'Población BDUA', '% ejecución', 'Población PAIS', COL_DISPLAY_PARTICIPACION]].style.format(TABLE_FORMAT),
                        use_container_width=True,
                        hide_index=True 
                    )
            else:
                st.info("No hay datos de Región/Subregión disponibles para mostrar la tabla.")
    
    # =========================================================================
    # --- PESTAÑA 3: Gráficos ---
    # =========================================================================
    with tab_charts:
        st.header("Análisis Gráfico")
        
        # --- 1. Gráfico de Cumplimiento Poblacional por Mes ---
        st.subheader("Población Presupuestada vs. Población Ejecutada por Mes")

        if df_chart_data_all_months.empty:
            st.info("No hay datos históricos para generar el gráfico mensual con los filtros seleccionados.")
        else:
            # 1. Agregación de datos por MES
            df_chart = df_chart_data_all_months.groupby("MES").agg(
                {'PRESUPUESTO': 'sum', 'POBLACION_BDUA': 'sum'}
            ).reset_index()
            
            # 2. Ordenamiento cronológico y limpieza de meses
            df_chart["MES_ORDER"] = df_chart["MES"].map(MONTH_ORDER)
            df_chart = df_chart.dropna(subset=["MES_ORDER"]).sort_values("MES_ORDER").copy()
            
            if df_chart.empty:
                 st.info("No hay datos de mes válidos para generar el gráfico.")
            else:
                
                # 3. Cálculo del Porcentaje de Ejecución: POBLACION_BDUA / PRESUPUESTO
                df_chart['PORCENTAJE_EJECUCION'] = np.where(
                    df_chart['PRESUPUESTO'] != 0,
                    (df_chart['POBLACION_BDUA'] / df_chart['PRESUPUESTO']) * 100,
                    0 
                )
            
                
                # 4. Creación de la etiqueta de texto para la anotación (Formato Porcentaje)
                df_chart['PCT_LABEL'] = df_chart['PORCENTAJE_EJECUCION'].apply(
                    lambda x: f"{x:,.1f}%" if pd.notna(x) and x >= 0 else "" 
                )
                
                # --- CONSTRUCCIÓN DEL GRÁFICO DE BARRAS AGRUPADAS ---
                
                fig = go.Figure(data=[
                    # Barra de Población Presupuestada (Objetivo)
                    go.Bar(
                        name='Presupuesto',
                        x=df_chart['MES'],
                        y=df_chart['PRESUPUESTO'],
                        marker_color='#a1a1aa', # Gris (Objetivo)
                        hovertemplate='Mes: %{x}<br>Presupuesto: %{y:,.0f}<extra></extra>'
                    ),
                    # Barra de Población Ejecutada (Real)
                    go.Bar(
                        name='Población BDUA',
                        x=df_chart['MES'], 
                        y=df_chart['POBLACION_BDUA'],
                        marker_color='#34A853', # Verde (Ejecutado)
                        hovertemplate='Mes: %{x}<br>Ejecutado (BDUA): %{y:,.0f}<extra></extra>'
                    )
                ])

                # Añadir las etiquetas de Porcentaje de Ejecución
                for i, row in df_chart.iterrows():
                    if row['PCT_LABEL']:
                        fig.add_annotation(
                            x=row['MES'],
                            y=row['POBLACION_BDUA'],
                            text=row['PCT_LABEL'],
                            showarrow=False,
                            yshift=10,
                            font=dict(color="black", size=10)
                        )

                # Configuración del layout
                fig.update_layout(
                    barmode='group',
                    title='Cumplimiento Poblacional Mensual (Presupuesto vs. Ejecutado BDUA)',
                    xaxis_title='Mes',
                    yaxis_title='Número de Población',
                    yaxis_tickformat=',.0f',
                    legend_title_text='Métrica',
                    yaxis=dict(rangemode='tozero')
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
        st.markdown("---")

        # --- 2. Comparación de Composición por Régimen ---
        st.subheader("Comparación de Composición por Régimen (Nueva EPS vs País)")
        if not df_regimen_long.empty:
            fig_regimen = px.bar(
                df_regimen_long, x='REGIMEN', y='Porcentaje', color='Tipo de Población', barmode='group',
                title='Composición de Población por Régimen (BDUA vs Total País)',
                labels={'Porcentaje': 'Porcentaje de la Población (%)', 'REGIMEN': 'Régimen de Salud'},
                text_auto='.1f', height=500,
                color_discrete_map={'% Participación NEP': '#4A90E2', '% Participación País': '#34A853'}
            )
            fig_regimen.update_layout(legend_title_text='Población')
            fig_regimen.update_yaxes(ticksuffix='%', range=[0, 100])
            st.plotly_chart(fig_regimen, use_container_width=True)
        else:
            st.info("No hay datos por régimen disponibles para mostrar el gráfico de composición.")

        st.markdown("---")


# ==============================================================================
# 4. EJECUCIÓN
# ==============================================================================
if __name__ == "__main__":
    poblacion_st()