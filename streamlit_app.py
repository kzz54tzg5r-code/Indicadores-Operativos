import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from io import BytesIO

# --- CONFIGURACIÓN EJECUTIVA ---
st.set_page_config(page_title="Price Shoes - Inteligencia Operativa", layout="wide", page_icon="📈")

# Estilos CSS
st.markdown("""
    <style>
    .section-header { color: #1F497D; font-weight: 800; font-size: 20px; margin-top: 30px; border-left: 6px solid #E6007E; padding-left: 12px; }
    .exec-card { background-color: #FDFDFD; border: 1px solid #EAEAEA; border-radius: 8px; padding: 20px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# --- MOTOR DE DATOS ---
@st.cache_data(ttl=600)
def load_business_data():
    URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSV6dtosg0Ydt0o3NMFezC--NjHfEW82onFeY2JR4PTYD3ylG4ZlRaQBquscFrCy_Lysrau9zTW6dkn/pub?output=xlsx"
    try:
        response = requests.get(URL, timeout=30)
        xls = pd.ExcelFile(BytesIO(response.content), engine='openpyxl')
        data_rows = []
        
        for sheet_name in xls.sheet_names:
            if not sheet_name.lower().startswith('sem'): continue
            df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            for i, row in df_raw.iterrows():
                if len(row) < 10: continue
                # Aquí ajustamos los índices según la estructura de tu archivo
                data_rows.append({
                    'Semana': sheet_name.strip(),
                    'Tienda': str(row[1]),
                    'Total_Ingresos': pd.to_numeric(row[2], errors='coerce'),
                    'Pzas_Hab': pd.to_numeric(row[10], errors='coerce'),
                    'Pzas_Ubi': pd.to_numeric(row[11], errors='coerce'),
                    'Meta_Rec': pd.to_numeric(row[7], errors='coerce'),
                    'Real_Rec': pd.to_numeric(row[8], errors='coerce')
                })
        return pd.DataFrame(data_rows).fillna(0)
    except: return pd.DataFrame()

df = load_business_data()

# --- INTERFAZ ---
st.title("📊 PRICE SHOES • Control Operativo")

if not df.empty:
    # 1. TARJETAS COMPARATIVAS (Últimas 4 semanas)
    semanas_lista = sorted(df['Semana'].unique(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))[-4:]
    cols_cards = st.columns(4)

    for i, sem in enumerate(semanas_lista):
        data_act = df[df['Semana'] == sem]
        val_ing = data_act['Total_Ingresos'].sum()
        delta = 0
        if i > 0:
            val_ant = df[df['Semana'] == semanas_lista[i-1]]['Total_Ingresos'].sum()
            delta = val_ing - val_ant
        
        with cols_cards[i]:
            st.metric(label=f"Semana {sem}", value=f"{int(val_ing):,}", delta=f"{int(delta):,}")

    st.markdown("---")
    
    # 2. PESTAÑAS
    tab1, tab2 = st.tabs(["📊 RESUMEN", "🚀 TENDENCIA"])
    
    with tab1:
        st.markdown('<p class="section-header">Distribución por Tienda</p>', unsafe_allow_html=True)
        fig_pie = go.Figure(data=[go.Pie(labels=df['Tienda'], values=df['Total_Ingresos'], hole=.4)])
        st.plotly_chart(fig_pie, use_container_width=True)

    with tab2:
        st.markdown('<p class="section-header">Tendencia de Ingreso vs Habilitación</p>', unsafe_allow_html=True)
        df_tend = df.groupby('Semana').agg({'Total_Ingresos':'sum', 'Pzas_Hab':'sum'}).reset_index()
        fig_tend = go.Figure()
        fig_tend.add_trace(go.Scatter(x=df_tend['Semana'], y=df_tend['Total_Ingresos'], name='Ingresos', line=dict(color='#1F497D', width=3)))
        fig_tend.add_trace(go.Scatter(x=df_tend['Semana'], y=df_tend['Pzas_Hab'], name='Habilitados', line=dict(color='#E6007E', width=3)))
        st.plotly_chart(fig_tend, use_container_width=True)

else:
    st.warning("Verificando conexión con Google Sheets...")
