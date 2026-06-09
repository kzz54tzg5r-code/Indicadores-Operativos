import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
from io import BytesIO
from datetime import datetime

# =========================================================================
# --- CONFIGURACIÓN EJECUTIVA ---
# =========================================================================
st.set_page_config(page_title="Price Shoes - Operational Scorecard", layout="wide", page_icon="🏢")

st.markdown("""
    <style>
    .main { background-color: #F4F7F9; }
    .main-title { color: #000000; font-size: 38px; font-weight: 900; letter-spacing: -1.5px; margin-bottom: 0px; }
    .sub-title { color: #E6007E; font-size: 15px; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 30px; }
    .kpi-container { background-color: white; border-radius: 12px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-top: 5px solid #1F497D; text-align: center; }
    .kpi-label { color: #666; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }
    .kpi-value { color: #1F497D; font-size: 28px; font-weight: 900; margin-bottom: 4px; }
    .kpi-sub { color: #E6007E; font-size: 13px; font-weight: 700; }
    .alert-card { padding: 12px; border-radius: 8px; margin-bottom: 12px; font-weight: bold; font-size: 13px; border-left: 6px solid; }
    .alert-red { background-color: #FEE2E2; color: #991B1B; border-color: #EF4444; }
    .alert-yellow { background-color: #FEF3C7; color: #92400E; border-color: #F59E0B; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_data():
    URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSV6dtosg0Ydt0o3NMFezC--NjHfEW82onFeY2JR4PTYD3ylG4ZlRaQBquscFrCy_Lysrau9zTW6dkn/pub?output=xlsx"
    try:
        response = requests.get(URL, timeout=30)
        xls = pd.ExcelFile(BytesIO(response.content), engine='openpyxl')
        
        all_data = []
        for sheet in xls.sheet_names:
            if 'sem' in sheet.lower():
                # Leemos la pestaña completa
                df_raw = pd.read_excel(xls, sheet_name=sheet, header=None, engine='openpyxl')
                
                # Buscamos los bloques de datos. En este archivo, parece haber un bloque por día.
                # Identificamos las filas donde 'Tienda' está en la columna B (index 1)
                header_rows = df_raw[df_raw[1] == 'Tienda'].index.tolist()
                
                for h_idx in header_rows:
                    # La fecha suele estar una fila arriba del encabezado 'Tienda' en la columna B
                    fecha_val = df_raw.iloc[h_idx-1, 1]
                    if not isinstance(fecha_val, datetime):
                        continue
                        
                    # Extraemos las 6 filas de datos (las tiendas: Vallejo, Arco Norte, Puebla Sur, Miravalle, Ecatepec, etc.)
                    # El bloque de datos tiene 15 columnas (B a P)
                    df_day = df_raw.iloc[h_idx+1 : h_idx+7, 1:16].copy()
                    df_day.columns = ['Tienda', 'Ing_Aduana_Sis', 'Ing_Aduana', 'Ing_Muertos', 'Ing_Cajas', 'Total_Ing', 
                                     'Meta_Rec', 'Real_Rec', 'Pzas_Rec', 'Pzas_Hab', 'Pzas_Ubi', 
                                     'Pct_Rec', 'Pct_Hab', 'Pct_Ubi', 'Extra']
                    
                    df_day['Fecha'] = fecha_val
                    df_day['Semana'] = sheet
                    all_data.append(df_day)
        
        if not all_data: return pd.DataFrame()
        
        df = pd.concat(all_data, ignore_index=True)
        df = df.dropna(subset=['Tienda'])
        
        # Limpieza de tipos
        cols_num = ['Total_Ing', 'Meta_Rec', 'Real_Rec', 'Pzas_Rec', 'Pzas_Hab', 'Pzas_Ubi']
        for col in cols_num:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        # Atributos de tiempo
        meses_dict = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
        df['Mes'] = df['Fecha'].dt.month.map(meses_dict)
        
        return df
    except Exception as e:
        st.error(f"Error de procesamiento: {e}")
        return pd.DataFrame()

df_raw = load_data()

if not df_raw.empty:
    # --- FILTROS ---
    st.sidebar.image("https://priceshoes.com/media/logo/stores/1/logo_price_shoes.png", width=160)
    sel_tiendas = st.sidebar.multiselect("Tiendas:", sorted(df_raw['Tienda'].unique().tolist()), default=df_raw['Tienda'].unique().tolist())
    sel_meses = st.sidebar.multiselect("Meses:", ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'], default=df_raw['Mes'].unique().tolist())
    
    df_f = df_raw[(df_raw['Tienda'].isin(sel_tiendas)) & (df_raw['Mes'].isin(sel_meses))]
    
    st.markdown('<p class="main-title">PRICE SHOES • Operational Scorecard</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">CONTROL DE RECUPERACIÓN Y RECORRIDOS</p>', unsafe_allow_html=True)

    # --- KPI CARDS ---
    ing = df_f['Total_Ing'].sum()
    hab = df_f['Pzas_Hab'].sum()
    ubi = df_f['Pzas_Ubi'].sum()
    rec_m = df_f['Meta_Rec'].sum()
    rec_r = df_f['Real_Rec'].sum()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="kpi-container"><p class="kpi-label">📥 Ingresos Totales</p><p class="kpi-value">{ing:,.0f}</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-container"><p class="kpi-label">✨ Habilitado</p><p class="kpi-value">{(hab/ing*100 if ing>0 else 0):.1f}%</p><p class="kpi-sub">{hab:,.0f} Pzas</p></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-container"><p class="kpi-label">📍 Ubicado</p><p class="kpi-value">{(ubi/ing*100 if ing>0 else 0):.1f}%</p><p class="kpi-sub">{ubi:,.0f} Pzas</p></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-container"><p class="kpi-label">🎯 Efic. Recorridos</p><p class="kpi-value">{(rec_r/rec_m*100 if rec_m>0 else 0):.1f}%</p><p class="kpi-sub">{rec_r:,.0f} de {rec_m:,.0f}</p></div>', unsafe_allow_html=True)

    # --- GRÁFICOS ---
    tab1, tab2 = st.tabs(["📈 TENDENCIAS", "📑 DETALLE"])
    with tab1:
        col_a, col_b = st.columns(2)
        with col_a:
            df_sem = df_f.groupby('Semana').agg({'Total_Ing':'sum', 'Pzas_Hab':'sum'}).reset_index()
            fig = px.line(df_sem, x='Semana', y=['Total_Ing', 'Pzas_Hab'], title="Evolución Ingreso vs Habilitado", color_discrete_sequence=['#1F497D', '#E6007E'])
            st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})
        with col_b:
            df_t = df_f.groupby('Tienda').agg({'Total_Ing':'sum', 'Pzas_Ubi':'sum'}).reset_index()
            fig2 = px.bar(df_t, x='Tienda', y=['Total_Ing', 'Pzas_Ubi'], barmode='group', title="Desempeño por Tienda", color_discrete_sequence=['#1F497D', '#E6007E'])
            st.plotly_chart(fig2, use_container_width=True, config={'staticPlot': True})

    with tab2:
        st.dataframe(df_f[['Fecha', 'Semana', 'Tienda', 'Total_Ing', 'Pzas_Hab', 'Pzas_Ubi', 'Real_Rec', 'Meta_Rec']], use_container_width=True)
else:
    st.info("📊 Conectando con la base de datos... Asegúrate de que el Google Sheet sea público.")
