import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from io import BytesIO

# =========================================================================
# --- CONFIGURACIÓN EJECUTIVA Y ESTILOS ---
# =========================================================================
st.set_page_config(page_title="Price Shoes - Inteligencia Operativa", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .main { background-color: #FFFFFF; }
    .main-title { color: #000000; font-size: 38px; font-weight: 900; margin-bottom: 0px; letter-spacing: -1px; }
    .sub-title { color: #E6007E; font-size: 14px; font-weight: 800; margin-top: -5px; text-transform: uppercase; letter-spacing: 2px; }
    .section-header { color: #1F497D; font-weight: 800; font-size: 20px; margin-top: 30px; margin-bottom: 15px; border-left: 6px solid #E6007E; padding-left: 12px; }
    .exec-card { background-color: #FDFDFD; border: 1px solid #EAEAEA; border-radius: 8px; padding: 20px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    </style>
    """, unsafe_allow_html=True)

# =========================================================================
# --- MOTOR DE DATOS INTELIGENTE ---
# =========================================================================
@st.cache_data(ttl=600)
def load_business_data():
    URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSV6dtosg0Ydt0o3NMFezC--NjHfEW82onFeY2JR4PTYD3ylG4ZlRaQBquscFrCy_Lysrau9zTW6dkn/pub?output=xlsx"
    try:
        response = requests.get(URL, timeout=30)
        xls = pd.ExcelFile(BytesIO(response.content), engine='openpyxl')
        data_rows = []
        tiendas_objetivo = ['Vallejo', 'Arco Norte', 'Puebla Sur', 'Miravalle', 'Ecatepec']
        meses_dict = {'enero':'Enero', 'febrero':'Febrero', 'marzo':'Marzo', 'abril':'Abril', 'mayo':'Mayo', 'junio':'Junio', 'julio':'Julio', 'agosto':'Agosto', 'septiembre':'Septiembre', 'octubre':'Octubre', 'noviembre':'Noviembre', 'diciembre':'Diciembre'}

        for sheet_name in xls.sheet_names:
            if not sheet_name.lower().strip().startswith('sem'): continue
            df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None, engine='openpyxl')
            curr_date = "Sin Fecha"
            for i, row in df_raw.iterrows():
                if len(row) < 2: continue
                val = str(row[1]).strip()
                if '2026' in val and ',' in val: curr_date = val; continue
                if any(t.lower() in val.lower() for t in tiendas_objetivo) and len(val) < 30:
                    try:
                        mes_ext = "Otros"
                        for k, v in meses_dict.items():
                            if k in curr_date.lower(): mes_ext = v; break
                        data_rows.append({
                            'Mes': mes_ext, 'Semana': sheet_name.strip(), 'Tienda': val,
                            'Ing_Sis': row[2], 'Ing_Muertos': row[4], 'Ing_Cajas': row[5],
                            'Meta_Rec': row[7], 'Real_Rec': row[8], 'Pzas_Rec': row[9],
                            'Pzas_Hab': row[10], 'Pzas_Ubi': row[11]
                        })
                    except: continue
        df = pd.DataFrame(data_rows)
        for col in ['Ing_Sis', 'Ing_Muertos', 'Ing_Cajas', 'Meta_Rec', 'Real_Rec', 'Pzas_Rec', 'Pzas_Hab', 'Pzas_Ubi']:
            df[col] = df[col].apply(lambda x: float(str(x).replace(',', '').replace('%', '').strip()) if pd.notna(x) else 0.0)
        df['Total_Ingresos'] = df['Ing_Sis'] + df['Ing_Muertos'] + df['Ing_Cajas']
        return df
    except: return pd.DataFrame()

df = load_business_data()

# --- INTERFAZ ---
col_logo, col_text = st.columns([1, 6])
with col_text:
    st.markdown('<p class="main-title">PRICE SHOES • Business Intelligence</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">CONTROL OPERATIVO DE RECUPERACIÓN (CAMBIOS Y MUERTOS)</p>', unsafe_allow_html=True)

if not df.empty:
    # FILTROS
    st.sidebar.markdown("### 🎛️ Filtros")
    meses_orden = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    meses_presentes = sorted(df['Mes'].unique().tolist(), key=lambda x: meses_orden.index(x) if x in meses_orden else 99)
    sel_mes = st.sidebar.selectbox("Periodo Mensual:", ["Anual"] + meses_presentes)
    df_mes = df if sel_mes == "Anual" else df[df['Mes'] == sel_mes]
    
    # --- NUEVA SECCIÓN: TARJETAS COMPARATIVAS 4 SEMANAS ---
    st.markdown('<p class="section-header">Desempeño Semanal Comparativo</p>', unsafe_allow_html=True)
    sem_list = sorted(df_mes['Semana'].unique().tolist(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))[-4:]
    cols = st.columns(4)
    for i, sem in enumerate(sem_list):
        current_val = df_mes[df_mes['Semana'] == sem]['Total_Ingresos'].sum()
        delta = 0
        if i > 0:
            prev_val = df_mes[df_mes['Semana'] == sem_list[i-1]]['Total_Ingresos'].sum()
            delta = current_val - prev_val
        with cols[i]:
            st.metric(label=f"Semana {sem}", value=f"{int(current_val):,}", delta=f"{int(delta):,}")
    
    # --- PESTAÑAS (ESTRUCTURA ORIGINAL) ---
    tab1, tab2, tab3 = st.tabs(["📊 RESUMEN EJECUTIVO", "🚀 PRODUCTIVIDAD Y RENDIMIENTO", "📑 AUDITORÍA DE DATOS"])

    with tab1:
        # Aquí va tu lógica de KPI y Gráficos originales...
        st.write("Contenido de Resumen Ejecutivo...")

    with tab2:
        # Aquí va tu lógica de Productividad...
        st.write("Contenido de Productividad...")

    with tab3:
        # Aquí va tu lógica de Auditoría...
        st.write("Contenido de Auditoría...")

else:
    st.info("📊 Esperando datos...")
