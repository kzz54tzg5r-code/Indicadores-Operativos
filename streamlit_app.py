import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuración de página
st.set_page_config(page_title="Price Shoes - Operaciones Ropa", layout="wide", page_icon="👚")

# Estilos CSS
st.markdown("""
    <style>
    .main-title { color: #000000; font-size: 34px; font-weight: 800; }
    .sub-title { color: #E6007E; font-size: 15px; font-weight: bold; text-transform: uppercase; }
    .graph-title { color: #1F497D; font-weight: bold; font-size: 18px; border-left: 5px solid #1F497D; padding-left: 10px; }
    .semana-header { background-color: #1F497D; color: white; text-align: center; padding: 6px; border-radius: 4px; }
    .kpi-card-nested { background-color: #F8F9FA; border: 1px solid #D9D9D9; border-radius: 4px; padding: 10px; text-align: center; }
    .kpi-label-nested { color: #555555; font-size: 11px; font-weight: bold; }
    .kpi-value-nested { color: #1F497D; font-size: 18px; font-weight: bold; }
    .kpi-pct-inline { color: #E6007E; font-size: 15px; font-weight: bold; }
    .tabla-auditoria { width: 100%; border-collapse: collapse; font-size: 13px; }
    .tabla-auditoria tr:first-child { background-color: #1F497D; color: white; }
    .cell-td { padding: 10px; border: 1px solid #D9D9D9; text-align: right; }
    .cell-center { padding: 10px; border: 1px solid #D9D9D9; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def get_operational_data():
    URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSV6dtosg0Ydt0o3NMFezC--NjHfEW82onFeY2JR4PTYD3ylG4ZlRaQBquscFrCy_Lysrau9zTW6dkn/pub?output=csv"
    df = pd.read_csv(URL )
    numeric_cols = ['Sis_Aduana', 'Fis_Aduana', 'Muertos', 'Cajas', 'Meta_Rec', 'Real_Rec', 'Recolectadas', 'Habilitadas', 'Ubicadas']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    df['Total_Ingresos'] = df['Sis_Aduana'] + df['Muertos'] + df['Cajas']
    dias = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
    df['Dia_Semana_Num'] = df['Fecha'].dt.dayofweek
    df['Dia_Nombre'] = df['Dia_Semana_Num'].map(dias)
    return df

df_master = get_operational_data()

st.markdown('<p class="main-title">👚 PRICE SHOES • Operaciones Ropa</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">CONTROL DE OPERACIONES ROPA (AUTOMATIZADO)</p>', unsafe_allow_html=True)

if not df_master.empty:
    tipo = st.sidebar.radio("Agrupar por:", ["Semana", "Mes"])
    if tipo == "Semana":
        sel = st.sidebar.selectbox("Semana:", sorted(df_master['Semana'].unique()))
        df_f = df_master[df_master['Semana'] == sel]
    else:
        sel = st.sidebar.selectbox("Mes:", ["Todos"] + sorted(df_master['Mes'].unique()))
        df_f = df_master if sel == "Todos" else df_master[df_master['Mes'] == sel]
    
    tienda = st.sidebar.selectbox("Tienda:", ["Todas"] + list(df_master['Tienda'].unique()))
    if tienda != "Todas":
        df_f = df_f[df_f['Tienda'] == tienda]

    # Visualización de KPIs y Gráficos (Resumido para el ejemplo)
    st.write(f"Mostrando datos para: {sel} - {tienda}")
    st.dataframe(df_f)
    
    # Gráfico de ejemplo
    fig = go.Figure(go.Bar(x=df_f['Tienda'], y=df_f['Total_Ingresos'], marker_color='#1F497D'))
    fig.update_layout(title="Ingresos por Tienda")
    st.plotly_chart(fig, use_container_width=True)
