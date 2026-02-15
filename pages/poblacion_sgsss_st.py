import pandas as pd
import streamlit as st
import plotly.express as px
import numpy as np 

# --- Configuración de Ruta ---
FILE_PATH = r"C:\Users\dmendozad\Documents\Py\DATOS\sispro.xlsx"
SHEET_NAME = "consolidado"

# ====================================================================
# 0. FUNCIONES AUXILIARES
# ====================================================================

def convert_df_to_csv(df):
    """Convierte el DataFrame a CSV para el botón de descarga."""
    return df.to_csv(index=False).encode('utf-8')

@st.cache_data
def load_data(file_path, sheet_name):
    """Carga el archivo Excel y lo cachea para un rendimiento rápido."""
    
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    
    # Conversión y limpieza de tipos de datos 
    df['TOTAL'] = pd.to_numeric(df['TOTAL'], errors='coerce').fillna(0)
    df['CONTRIBUTIVO'] = pd.to_numeric(df['CONTRIBUTIVO'], errors='coerce').fillna(0)
    df['SUBSIDIADO'] = pd.to_numeric(df['SUBSIDIADO'], errors='coerce').fillna(0)
    df['ENTIDAD'] = df['ENTIDAD'].astype(str).str.upper().str.strip()
    
    return df

# ====================================================================
# 2. FUNCIÓN PRINCIPAL DEL DASHBOARD SISPRO (Punto de entrada con Filtro)
# ====================================================================

def main():
    """Función que maneja la carga de datos, el filtro de período y el renderizado."""
    
    try:
        df_data = load_data(FILE_PATH, SHEET_NAME)
    except FileNotFoundError:
        st.error(f"¡Error! No se encontró el archivo en la ruta: **{FILE_PATH}**")
        return
    except ValueError:
        st.error(f"¡Error! No se encontró la hoja **'{SHEET_NAME}'** en el archivo Excel.")
        return
    except Exception as e:
        st.error(f"Ocurrió un error al cargar los datos: {e}")
        return

    if df_data is not None:
        
        # --- IMPLEMENTACIÓN DEL FILTRO DE PERÍODO EN LA BARRA LATERAL ---
        st.sidebar.title("Filtros Globales ⚙️")
        
        # Obtener períodos únicos, ordenados de forma descendente (más reciente primero)
        periodos = sorted(df_data['PERIODO'].unique().tolist(), reverse=True)
        
        # Insertar la opción "Acumulado"
        periodos.insert(0, "ACUMULADO (Todos los Períodos)")
        
        periodo_seleccionado = st.sidebar.selectbox(
            "Selecciona el Período:", 
            periodos, 
            index=0 
        )
        
        # 1. Aplicar el Filtro al DataFrame
        if periodo_seleccionado != "ACUMULADO (Todos los Períodos)":
            df_filtrado = df_data[df_data['PERIODO'] == periodo_seleccionado].copy()
            st.sidebar.info(f"Mostrando datos del Período: **{periodo_seleccionado}**")
        else:
            df_filtrado = df_data.copy()
            st.sidebar.info("Mostrando datos: **Acumulado Total**")
            
        # Almacenar la selección del período para usarla en el nombre del archivo de descarga (Pestaña 1)
        st.session_state['periodo_seleccionado'] = periodo_seleccionado

        # 2. Llamar a la función principal pasando el DataFrame filtrado y el DataFrame original
        crear_dashboard(df_filtrado, df_data)

# ====================================================================
# 3. FUNCIÓN DE CREACIÓN DE PESTAÑAS (Recibe dos DataFrames)
# ====================================================================

def crear_dashboard(df_filtrado: pd.DataFrame, df_original: pd.DataFrame):
    """Crea el dashboard interactivo de Streamlit usando df_filtrado para la mayoría de pestañas
       y df_original solo para Evolución Temporal."""
    
    st.title("Seguimiento a la Población SGSSS - (SISPRO)")
    st.write("---")

    # Definición de las 4 pestañas
    tab1, tab2, tab3, tab4 = st.tabs([
        "Ranking EPS", 
        "Evolución Poblacion Afiliada", 
        "EPS por Departamento", 
        "Perfil de Afiliados por EPS"
    ])

    # ----------------------------------------------------------------
    # --- PESTAÑA 1: Ranking EPS por Total 
    # ----------------------------------------------------------------
    with tab1:
        st.header("Participación EPS en el SGSSS")

        # 1. Preparación de Datos
        df_eps = df_filtrado.groupby('ENTIDAD').agg({ 
            'TOTAL': 'sum', 
            'CONTRIBUTIVO': 'sum', 
            'SUBSIDIADO': 'sum'
        }).reset_index().sort_values(by='TOTAL', ascending=False)
        
        # Lógica de Agrupación 'OTRAS EPS'
        top_10_eps = df_eps.head(10)['ENTIDAD'].tolist()
        df_agrupado = df_eps.copy()
        
        # Añadir columna de agrupamiento
        df_agrupado['ENTIDAD_AGRUPADA'] = df_agrupado['ENTIDAD'].apply(
            lambda x: x if x in top_10_eps else "OTRAS EPS"
        )
        
        # Datos para el ranking (Top 10 + OTRAS EPS agregadas)
        df_ranking_final = df_agrupado.groupby('ENTIDAD_AGRUPADA').sum().reset_index()
        total_poblacion = df_ranking_final['TOTAL'].sum() 

        # Calcular el porcentaje de participación
        df_ranking_final['Participación (%)'] = (df_ranking_final['TOTAL'] / total_poblacion) * 100
        
        # Separar 'OTRAS EPS' para ordenarlas al final
        otras_eps_row = df_ranking_final[df_ranking_final['ENTIDAD_AGRUPADA'] == "OTRAS EPS"]
        df_ranking_sin_otras = df_ranking_final[df_ranking_final['ENTIDAD_AGRUPADA'] != "OTRAS EPS"]
        
        # 2. Reordenar (Top 10 ordenado + OTRAS EPS al final)
        df_chart_final = pd.concat([
            df_ranking_sin_otras.sort_values(by='TOTAL', ascending=False),
            otras_eps_row
        ], ignore_index=True)


        # 3. Gráfico de Barras con Etiquetas de Porcentaje 
        fig = px.bar(
            df_chart_final, 
            x='ENTIDAD_AGRUPADA', 
            y='TOTAL', 
            title='Participación de Afiliados (Total) - Top 10 vs. Otras EPS',
            labels={'ENTIDAD_AGRUPADA': 'EPS', 'TOTAL': 'Total de Afiliados'},
            color='TOTAL',
            color_continuous_scale=px.colors.sequential.Plotly3,
            text=df_chart_final['Participación (%)'].apply(lambda x: f'{x:.2f}%') # Etiqueta de Porcentaje
        )
        
        fig.update_traces(textposition='inside') 
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.write("---")

        # 4. Tabla de Ranking Detallada 
        st.subheader("Tablas de Participación por Régimen")
        
        # Preparar la tabla de ranking (Top 10 + OTRAS EPS al final)
        df_tabla_descarga = df_chart_final[['ENTIDAD_AGRUPADA', 'CONTRIBUTIVO', 'SUBSIDIADO', 'TOTAL']].copy()
        df_tabla_descarga.columns = ['EPS', 'CONTRIBUTIVO', 'SUBSIDIADO', 'TOTAL']
        
        df_tabla_mostrar = df_tabla_descarga.copy()

        # Formato de números con separador de miles (solo para mostrar)
        df_tabla_mostrar['CONTRIBUTIVO'] = df_tabla_mostrar['CONTRIBUTIVO'].map('{:,.0f}'.format)
        df_tabla_mostrar['SUBSIDIADO'] = df_tabla_mostrar['SUBSIDIADO'].map('{:,.0f}'.format)
        df_tabla_mostrar['TOTAL'] = df_tabla_mostrar['TOTAL'].map('{:,.0f}'.format)

        # Mostrar la tabla
        st.dataframe(
            df_tabla_mostrar.rename(columns=lambda x: x.upper()), 
            hide_index=True,
            use_container_width=True,
            column_order=['EPS', 'CONTRIBUTIVO', 'SUBSIDIADO', 'TOTAL'] 
        )
        
        # BOTÓN DE DESCARGA PARA LA TABLA PRINCIPAL
        csv_ranking = convert_df_to_csv(df_tabla_descarga)
        st.download_button(
            label="⬇️ Exportar Ranking Principal a CSV",
            data=csv_ranking,
            file_name=f'ranking_eps_{st.session_state.get("periodo_seleccionado", "acumulado").replace(" ", "_")}.csv',
            mime='text/csv',
            key='download_ranking_principal'
        )
        st.markdown('---')


        # Contenido para la opción expandir de 'Otras EPS'
        otras_eps_data = df_agrupado[df_agrupado['ENTIDAD_AGRUPADA'] == "OTRAS EPS"].copy()
        
        with st.expander("🔎 VER DETALLE DE OTRAS EPS"):
            # Preparar tabla detalle de otras EPS (para mostrar y descargar)
            df_otras_detalle_descarga = otras_eps_data.drop(columns=['ENTIDAD_AGRUPADA']).copy()
            df_otras_detalle_descarga.rename(columns={'ENTIDAD': 'EPS', 'CONTRIBUTIVO': 'Contributivo', 'SUBSIDIADO': 'Subsidiado', 'TOTAL': 'Total'}, inplace=True)
            
            df_otras_detalle_mostrar = df_otras_detalle_descarga.copy()
            
            # Formato de números con separador de miles (solo para mostrar)
            df_otras_detalle_mostrar['Contributivo'] = df_otras_detalle_mostrar['Contributivo'].map('{:,.0f}'.format)
            df_otras_detalle_mostrar['Subsidiado'] = df_otras_detalle_mostrar['Subsidiado'].map('{:,.0f}'.format)
            df_otras_detalle_mostrar['Total'] = df_otras_detalle_mostrar['Total'].map('{:,.0f}'.format)
            
            st.dataframe(
                df_otras_detalle_mostrar.rename(columns=lambda x: x.upper()), 
                hide_index=True,
                use_container_width=True
            )
            
            # BOTÓN DE DESCARGA PARA OTRAS EPS
            csv_otras = convert_df_to_csv(df_otras_detalle_descarga)
            st.download_button(
                label="⬇️ Exportar Detalle 'Otras EPS' a CSV",
                data=csv_otras,
                file_name=f'detalle_otras_eps_{st.session_state.get("periodo_seleccionado", "acumulado").replace(" ", "_")}.csv',
                mime='text/csv',
                key='download_otras_eps'
            )


    # ----------------------------------------------------------------
    # --- PESTAÑA 2: Evolución Temporal
    # ----------------------------------------------------------------
    with tab2:
        st.header("Evolución de la población por EPS")
        st.info("Seleccione las EPS que va a comparar y el regimen.")
        
        # Preparación de datos para la evolución (USA df_original)
        df_evolucion = df_original.groupby(['PERIODO', 'ENTIDAD']).agg({ 
            'CONTRIBUTIVO': 'sum',
            'SUBSIDIADO': 'sum',
            'TOTAL': 'sum'
        }).reset_index()
        
        opciones_regimen = ['TOTAL', 'CONTRIBUTIVO', 'SUBSIDIADO']
        eps_unicas = sorted(df_evolucion['ENTIDAD'].unique().tolist())
        
        # --- CONTROL DE FILTRO: Selección Múltiple ---
        col_filtro1, col_filtro2 = st.columns([3, 1])
        
        with col_filtro1:
            # Permite seleccionar hasta 3 EPS
            eps_seleccionadas = st.multiselect(
                "Selecciona las EPS a comparar (Máx. 3):", 
                eps_unicas,
                default=eps_unicas[:3] 
            )
        
        with col_filtro2:
            regimen_seleccionado = st.selectbox(
                "Régimen:", 
                opciones_regimen
            )
        
        if eps_seleccionadas:
            # 1. Datos de las EPS seleccionadas
            df_final_evolucion = df_evolucion[df_evolucion['ENTIDAD'].isin(eps_seleccionadas)].copy()

            # --- CÁLCULO DEL PORCENTAJE DE CRECIMIENTO ---
            if not df_final_evolucion.empty:
                
                # Obtener la lista de períodos ordenados
                periodos_ordenados = sorted(df_final_evolucion['PERIODO'].unique())
                
                if len(periodos_ordenados) >= 2:
                    
                    # Encontrar el primer y el último período
                    periodo_inicial = periodos_ordenados[0]
                    periodo_final = periodos_ordenados[-1]

                    crecimiento_data = []

                    for eps in eps_seleccionadas:
                        df_eps = df_final_evolucion[df_final_evolucion['ENTIDAD'] == eps]
                        
                        # Valor inicial
                        total_inicial = df_eps[df_eps['PERIODO'] == periodo_inicial][regimen_seleccionado].sum()
                        
                        # Valor final
                        total_final = df_eps[df_eps['PERIODO'] == periodo_final][regimen_seleccionado].sum()

                        crecimiento = 0.0
                        
                        if total_inicial > 0:
                            crecimiento = ((total_final - total_inicial) / total_inicial) * 100
                        elif total_inicial == 0 and total_final > 0:
                            crecimiento = np.inf 
                        
                        crecimiento_data.append({
                            'EPS': eps,
                            'Crecimiento': crecimiento
                        })
                    
                    df_crecimiento = pd.DataFrame(crecimiento_data)
                    
                    # --- VISUALIZACIÓN DEL CRECIMIENTO ---
                    st.subheader(f"Crecimiento acumulado de la EPS ({regimen_seleccionado}) desde **{periodo_inicial}** hasta **{periodo_final}**")
                    
                    # Crear columnas para mostrar el crecimiento de cada EPS
                    cols_crecimiento = st.columns(len(df_crecimiento))
                    
                    for idx, row in df_crecimiento.iterrows():
                        
                        # Lógica de corrección para st.metric
                        if row['Crecimiento'] == np.inf:
                            valor_crecimiento = "📈 Crecimiento >1000%"
                            delta_color_val = 'normal' 
                        else:
                            valor_crecimiento = f"{row['Crecimiento']:+.2f}%"
                            delta_color_val = 'normal' 

                        with cols_crecimiento[idx]:
                            st.metric(
                                label=row['EPS'], 
                                value=valor_crecimiento, 
                                delta=None,
                                delta_color=delta_color_val
                            )
                    st.write("---") # Separador visual
                
                else:
                    st.warning("Se necesita al menos dos períodos de datos para calcular el crecimiento temporal.")


            # --- Gráfico de BARRAS Agrupadas ---
            fig2 = px.bar(
                df_final_evolucion,
                x='PERIODO',
                y=regimen_seleccionado,
                color='ENTIDAD', 
                barmode='group', 
                title=f'Evolución del Régimen {regimen_seleccionado} - Comparación de Entidades Seleccionadas',
                labels={'PERIODO': 'Período', regimen_seleccionado: f'Afiliados ({regimen_seleccionado})', 'ENTIDAD': 'EPS'},
            )
            fig2.update_xaxes(type='category', tickangle=45) 
            st.plotly_chart(fig2, use_container_width=True)
            
            # --- TABLA Y DESCARGA DE DATOS ---
            st.write("---")
            st.subheader("Tabla de Datos de Evolución")
            
            df_tabla_evolucion_descarga = df_final_evolucion.copy()
            
            # Formateo para la visualización
            df_tabla_evolucion_mostrar = df_tabla_evolucion_descarga.copy()
            for col in ['TOTAL', 'CONTRIBUTIVO', 'SUBSIDIADO']:
                df_tabla_evolucion_mostrar[col] = df_tabla_evolucion_mostrar[col].map('{:,.0f}'.format)
            
            st.dataframe(df_tabla_evolucion_mostrar, hide_index=True, use_container_width=True)
            
            # Botón de descarga
            csv_evolucion = convert_df_to_csv(df_tabla_evolucion_descarga)
            st.download_button(
                label="⬇️ Exportar Datos de Evolución a CSV",
                data=csv_evolucion,
                file_name='evolucion_temporal_sgsss_seleccionadas.csv',
                mime='text/csv',
                key='download_evolucion'
            )
        else:
            st.warning("Por favor, selecciona al menos una EPS para ver la evolución.")


    # ----------------------------------------------------------------
    # --- PESTAÑA 3: Población por Departamento (TABLA PIVOTANTE TOP 5) ---
    # ----------------------------------------------------------------
    with tab3:
        # Definición del límite del Top N
        N_TOP = 10
        st.header(f"EPS por Departamento y Régimen")
        
        # 1. Filtro de Régimen
        opciones_regimen_depto = ['TOTAL', 'CONTRIBUTIVO', 'SUBSIDIADO']
        regimen_depto_seleccionado = st.selectbox(
            "Selecciona el Régimen para el análisis departamental:", 
            opciones_regimen_depto
        )

        # 2. Preparación y Agrupación de Datos
        df_filtrado['DEPTO'].replace('', np.nan, inplace=True)
        df_depto_data = df_filtrado.dropna(subset=['DEPTO']).copy()
        
        df_agrupado_por_depto_eps = df_depto_data.groupby(['DEPTO', 'ENTIDAD']).sum(numeric_only=True).reset_index()
        
        # Lista de departamentos únicos
        deptos_unicos = sorted(df_agrupado_por_depto_eps['DEPTO'].unique().tolist())
        
        # Inicializar la lista de resultados de la tabla (Pivotante)
        tabla_final_data = []

        for depto in deptos_unicos:
            # Filtrar por departamento y ordenar por el régimen seleccionado
            df_depto = df_agrupado_por_depto_eps[df_agrupado_por_depto_eps['DEPTO'] == depto].copy()
            df_depto_sorted = df_depto.sort_values(by=regimen_depto_seleccionado, ascending=False)
            
            # Calcular el total del departamento para el régimen seleccionado
            total_depto_regimen = df_depto[regimen_depto_seleccionado].sum()

            # Obtener el Top N para ese departamento y régimen
            df_top_n = df_depto_sorted.head(N_TOP)

            # Construir la fila de la tabla final
            row_data = {
                'DEPARTAMENTO': depto,
                f'POBLACIÓN TOTAL ({regimen_depto_seleccionado})': total_depto_regimen,
            }
            
            # Llenar las columnas del Top N
            for i in range(N_TOP):
                if i < len(df_top_n):
                    # Nombre de la EPS, su valor y su participación
                    eps_name = df_top_n.iloc[i]['ENTIDAD']
                    eps_value = df_top_n.iloc[i][regimen_depto_seleccionado]
                    eps_participacion = (eps_value / total_depto_regimen) * 100 if total_depto_regimen > 0 else 0
                    
                    row_data[f'EPS TOP {i+1}'] = eps_name
                    row_data[f'AFILIADOS TOP {i+1}'] = eps_value
                    row_data[f'PARTICIPACIÓN TOP {i+1} (%)'] = eps_participacion
                else:
                    # Llenar con NaN o 0 si no hay suficientes EPS
                    row_data[f'EPS TOP {i+1}'] = np.nan
                    row_data[f'AFILIADOS TOP {i+1}'] = 0
                    row_data[f'PARTICIPACIÓN TOP {i+1} (%)'] = 0
            
            tabla_final_data.append(row_data)

        df_tabla_final_descarga = pd.DataFrame(tabla_final_data)
        
        # --- Visualización y Formato ---
        st.subheader(f"EPS para el Régimen: **{regimen_depto_seleccionado}**")
        
        # 3. Formato para mostrar
        df_tabla_final_mostrar = df_tabla_final_descarga.copy()
        
        for col in df_tabla_final_mostrar.columns:
            if 'AFILIADOS' in col or 'POBLACIÓN' in col:
                # Aplicar formato de miles a las columnas de números
                df_tabla_final_mostrar[col] = df_tabla_final_mostrar[col].map('{:,.0f}'.format)
            elif 'PARTICIPACIÓN' in col:
                # Aplicar formato de porcentaje
                df_tabla_final_mostrar[col] = df_tabla_final_mostrar[col].map('{:.2f}%'.format)
                
        # Definir el orden de las columnas para la visualización
        columnas_ordenadas = [
            'DEPARTAMENTO', 
            f'POBLACIÓN TOTAL ({regimen_depto_seleccionado})', 
            'EPS TOP 1', 'AFILIADOS TOP 1', 'PARTICIPACIÓN TOP 1 (%)',
            'EPS TOP 2', 'AFILIADOS TOP 2', 'PARTICIPACIÓN TOP 2 (%)',
            'EPS TOP 3', 'AFILIADOS TOP 3', 'PARTICIPACIÓN TOP 3 (%)',
            'EPS TOP 4', 'AFILIADOS TOP 4', 'PARTICIPACIÓN TOP 4 (%)',
            'EPS TOP 5', 'AFILIADOS TOP 5', 'PARTICIPACIÓN TOP 5 (%)',
        ]

        st.dataframe(
            df_tabla_final_mostrar[columnas_ordenadas].rename(columns=lambda x: x.upper()), 
            hide_index=True, 
            use_container_width=True
        )

        # 4. BOTÓN DE DESCARGA (Descarga el Top 5 Pivotado)
        csv_depto_top5 = convert_df_to_csv(df_tabla_final_descarga)
        st.download_button(
            label=f"⬇️ Exportar Ranking Top {N_TOP} Departamental ({regimen_depto_seleccionado}) a CSV",
            data=csv_depto_top5,
            file_name=f'ranking_departamental_TOP{N_TOP}_{regimen_depto_seleccionado.lower()}_{st.session_state.get("periodo_seleccionado", "acumulado").replace(" ", "_")}.csv',
            mime='text/csv',
            key='download_depto_top5'
        )


    # ----------------------------------------------------------------
    # --- PESTAÑA 4: Perfil de Afiliados (1 COLUMNA - ESPACIO MÁXIMO) ---
    # ----------------------------------------------------------------
    with tab4:
        st.header("👤 Perfil de Afiliados a Nivel Nacional")
        
        eps_unicas = sorted(df_filtrado['ENTIDAD'].unique().tolist()) 
        eps_perfil_seleccionada = st.selectbox(
            "Selecciona una EPS para analizar su perfil:", 
            eps_unicas, 
            index=0,
            key='perfil_eps_select' 
        )

        df_perfil_eps = df_filtrado[df_filtrado['ENTIDAD'] == eps_perfil_seleccionada].copy() 
        
        # Columnas a analizar
        dimensiones = ['GENERO', 'TIPO_AFILIADO', 'TIPO_POBLACION', 'TERRITORIALIDAD']
        
        # Iterar sobre las dimensiones y crear una tabla por cada una en una sola columna
        for i, dim in enumerate(dimensiones):
            
            st.subheader(f"{dim.replace('_', ' ').title()}")
            
            # Línea divisoria para separar visualmente cada tabla (excepto la primera)
            if i > 0:
                st.write("---") 

            df_dim = df_perfil_eps.groupby(dim).sum(numeric_only=True).reset_index()
            total_eps = df_dim['TOTAL'].sum()

            # Cálculo de Porcentaje
            df_dim['Porcentaje'] = (df_dim['TOTAL'] / total_eps) * 100
            
            # Formato de la tabla (para mostrar y descargar)
            df_tabla_dim_descarga = df_dim[[dim, 'TOTAL', 'Porcentaje']].rename(
                columns={'TOTAL': 'Afiliados', 'Porcentaje': 'Participación (%)'}
            ).sort_values(by='Afiliados', ascending=False)
            
            df_tabla_dim_mostrar = df_tabla_dim_descarga.copy()
            df_tabla_dim_mostrar['Participación (%)'] = df_tabla_dim_mostrar['Participación (%)'].map('{:.2f}%'.format)
            df_tabla_dim_mostrar['Afiliados'] = df_tabla_dim_mostrar['Afiliados'].map('{:,.0f}'.format)
            
            # Mostrar la tabla (usando el ancho completo del contenedor de la pestaña)
            st.dataframe(df_tabla_dim_mostrar.rename(columns=lambda x: x.upper()), hide_index=True, use_container_width=True)
            
            # BOTÓN DE DESCARGA PARA EL PERFIL
            csv_perfil = convert_df_to_csv(df_tabla_dim_descarga)
            st.download_button(
                label=f"⬇️ Exportar {dim.replace('_', ' ').title()} a CSV",
                data=csv_perfil,
                file_name=f'perfil_{eps_perfil_seleccionada.lower().replace(" ", "_")}_{dim.lower()}.csv',
                mime='text/csv',
                key=f'download_perfil_{dim}'
            )

# ====================================================================
# 4. LLAMADA DE EJECUCIÓN 
# ====================================================================
main()