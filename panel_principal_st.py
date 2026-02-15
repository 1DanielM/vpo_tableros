import streamlit as st
import pandas as pd
import altair as alt
import os

# ===== CONFIGURACIÓN DE LA PÁGINA STREAMLIT =====
st.set_page_config(
    page_title="TABLEROS DE SEGUIMIENTO VPO",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ====== FONDO BLANCO ======
st.markdown("""
    <style>
        .main {
            background-color: white !important;
        }
        .stApp {
            background-color: white !important;
        }
        .block-container {
            background-color: white !important;
        }
    </style>
""", unsafe_allow_html=True)

# ===== OCULTAR BARRA LATERAL =====
hide_sidebar = """
    <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="collapsedControl"] {display: none;}
    </style>
"""
st.markdown(hide_sidebar, unsafe_allow_html=True)


# ===== ESTILOS PERSONALIZADOS =====
st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] {
            background-color: #1E3050;
        }
        .main .block-container {
            padding-top: 2rem;
        }
        .titulo-principal {
            font-size: 36px;
            font-weight: bold;
            color: white;
            background-color: #1E3050;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 30px;
        }
        .stButton>button {
            width: 100% !important;
            height: 40px !important;
            font-size: 14px !important;
            border-radius: 10px !important;
        }
        .footer {
            text-align: center;
            color: #0B2545;
            font-size: 14px;
            margin-top: 40px;
        }
    </style>
""", unsafe_allow_html=True)

# ===== TÍTULO PRINCIPAL =====
st.image("logo2.png", width=150)
st.markdown('<div class="titulo-principal">📊 TABLEROS DE SEGUIMIENTO</div>', unsafe_allow_html=True)

# ===== BOTONES DE NAVEGACIÓN =====
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("INGRESO MENSUAL UPC", use_container_width=True):
        st.switch_page("pages/ingreso_st.py")

with col2:
    if st.button("POBLACION BDUA", use_container_width=True):
        st.switch_page("pages/poblacion_st.py")

with col3:
    if st.button("POBLACION SGSSS", use_container_width=True):
        st.switch_page("pages/poblacion_sgsss_st.py")

with col4:
    if st.button("SEGUIMIENTO INGRESO Y POBLACION", use_container_width=True):
        st.switch_page("pages/ingreso_poblacion_st.py")

        

# ===== PIE DE PÁGINA =====
st.markdown("""
    <div class="footer">
        VICEPRESIDENCIA DE OPERACIONES · NUEVA EPS
    </div>
""", unsafe_allow_html=True)
