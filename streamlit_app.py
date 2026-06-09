import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from io import BytesIO

# =========================================================================
# --- CONFIGURACIÓN DE INTERFAZ Y ESTILOS ---
# =========================================================================
st.set_page_config(page_title="Price Shoes - Operaciones Ropa", layout="wide", page_icon="👚")

st.markdown("""
    <style>
    .main-title { color: #000000; font-size: 34px; font-weight: 800; margin-bottom: 0px; }
    .sub-title { color: #E6007E; font-size: 15px; font-weight: bold; margin-top: -5px; text-transform: uppercase; }
    .graph-title { color: #1F497D; font-weight: bold; font-size: 18px; margin-top: 35px; margin-bottom: 15px; border-left: 5px solid #1F497D; padding-left: 10px; }
    .kpi-card { background-color: #F8F9FA; border: 1px solid #D9D9D9; border-radius: 4px; padding: 15px; text-align: center; }
    .kpi-label { color: #555555; font-size: 12px; font-weight: bold; }
    .kpi-value { color: #1F497D; font-size: 22px; font-weight: bold; }
    .kpi-pct { color: #E6007E; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# =========================================================================
# --- MOTOR DE CARGA MULTI-PESTAÑA (EXCEL) ---
# =========================================================================
@st.cache_data(ttl=600)
def load_all_data():
    SHEET_ID = "1vSV6dtosg0Ydt0o3NMFezC--NjHfEW82onFeY2JR4PTYD3ylG4ZlRaQBquscFrCy_Lysrau9zTW6dkn"
    # URL de exportación XLSX
    URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"
    
    try:
        response = requests.get(URL, timeout=15)
        response.raise_for_status() # Verificar que la descarga fue exitosa
        
        # Usar openpyxl explícitamente como motor
        xls = pd.ExcelFile(BytesIO(response.content), engine='openpyxl')
        
        data_rows = []
        tiendas_objetivo = ['Vallejo', 'Arco Norte', 'Puebla Sur', 'Miravalle', 'Ecatepec']
        
        for sheet_name in xls.sheet_names:
            if not sheet_name.lower().startswith('sem'): continue
            
            # Leer pestaña sin cabeceras
            df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None, engine='openpyxl')
            current_date = "Sin Fecha"
            
            for i, row in df_raw.iterrows():
                val = str(row[1]).strip() if len(row) > 1 else ""
                
                # Detectar fecha
                if '2026' in val and ',' in val:
                    current_date = val
                    continue
                
                # Detectar tienda
                if any(t in val for t in tiendas_objetivo) and len(val) < 25:
                    try:
                        data_rows.append({
                            'Mes': 'Mayo' if 'mayo' in current_date.lower() else ('Junio' if 'junio' in current_date.lower() else 'Julio-Dic'),
                            'Semana': sheet_name.strip(),
                            'Tienda': val,
                            'Sis_Aduana': row[2],
                            'Muertos': row[4],
                            'Cajas': row[5],
                            'Meta_Rec': row[7],
                            'Real_Rec': row[8],
                            'Habilitadas': row[10],
                            'Ubicadas': row[11]
                        })
                    except: continue

        if not data_rows:
            return pd.DataFrame()
            
        df = pd.DataFrame(data_rows)
        
        # Limpieza numérica
        def clean(x):
            try:
                s = str(x).replace(',', '').replace('%', '').strip()
                return float(s)
            except: return 0.0

        num_cols = ['Sis_Aduana', 'Muertos', 'Cajas', 'Meta_Rec', 'Real_Rec', 'Habilitadas', 'Ubicadas']
        for col in num_cols:
            df[col] = df[col].apply(clean)
        
        df['Total_Ingresos'] = df['Sis_Aduana'] + df['Muertos'] + df['Cajas']
        return df
    except Exception as e:
        st.error(f"Error de conexión o formato: {e}")
        return pd.DataFrame()

# =========================================================================
# --- INTERFAZ ---
# =========================================================================
df = load_all_data()

st.markdown('<p class="main-title">👚 PRICE SHOES • Operaciones Ropa</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">DASHBOARD ANUAL CONSOLIDADO</p>', unsafe_allow_html=True)

if not df.empty:
    st.sidebar.markdown("### 🔍 Filtros")
    
    # Filtro Mes
    meses_disponibles = sorted(df['Mes'].unique().tolist())
    sel_mes = st.sidebar.selectbox("Mes:", ["Todos"] + meses_disponibles)
    df_mes = df if sel_mes == "Todos" else df[df['Mes'] == sel_mes]
    
    # Filtro Semana
    semanas_disponibles = sorted(df_mes['Semana'].unique().tolist(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    sel_sem = st.sidebar.selectbox("Semana:", ["Todas"] + semanas_disponibles)
    
    # Filtro Tienda
    tiendas_disponibles = sorted(df['Tienda'].unique().tolist())
    sel_tienda = st.sidebar.selectbox("Tienda:", ["Todas"] + tiendas_disponibles)

    # Aplicar Filtros
    df_f = df_mes.copy()
    if sel_sem != "Todas": df_f = df_f[df_f['Semana'] == sel_sem]
    if sel_tienda != "Todas": df_f = df_f[df_f['Tienda'] == sel_tienda]

    # Visualización
    st.markdown(f"### 📊 Reporte: {sel_mes} / {sel_sem} / {sel_tienda}")
    
    c1, c2, c3, c4 = st.columns(4)
    ing, hab, ubi = df_f['Total_Ingresos'].sum(), df_f['Habilitadas'].sum(), df_f['Ubicadas'].sum()
    met, rea = df_f['Meta_Rec'].sum(), df_f['Real_Rec'].sum()
    
    c1.markdown(f'<div class="kpi-card"><p class="kpi-label">📥 INGRESOS</p><p class="kpi-value">{ing:,.0f}</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><p class="kpi-label">✨ HABILITADO</p><p class="kpi-value">{hab:,.0f} <small class="kpi-pct">({(hab/ing*100 if ing>0 else 0):.1f}%)</small></p></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><p class="kpi-label">📍 UBICADO</p><p class="kpi-value">{ubi:,.0f} <small class="kpi-pct">({(ubi/ing*100 if ing>0 else 0):.1f}%)</small></p></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-card"><p class="kpi-label">🎯 RECORRIDOS</p><p class="kpi-value">{(rea/met*100 if met>0 else 0):.1f}%</p></div>', unsafe_allow_html=True)

    # Gráfico Evolución
    if sel_sem == "Todas":
        st.markdown('<p class="graph-title">Evolución Semanal</p>', unsafe_allow_html=True)
        df_t = df_f.groupby('Semana').agg({'Total_Ingresos':'sum', 'Habilitadas':'sum'}).reset_index()
        df_t['n'] = df_t['Semana'].apply(lambda x: int(''.join(filter(str.isdigit, x)) or 0))
        df_t = df_t.sort_values('n')
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_t['Semana'], y=df_t['Total_Ingresos'], name="Ingresos", line=dict(color='#1F497D', width=3)))
        fig.add_trace(go.Scatter(x=df_t['Semana'], y=df_t['Habilitadas'], name="Habilitado", line=dict(color='#E6007E', width=3)))
        st.plotly_chart(fig, use_container_width=True)

    # Ranking
    st.markdown('<p class="graph-title">Desempeño por Tienda</p>', unsafe_allow_html=True)
    df_g = df_f.groupby('Tienda').agg({'Total_Ingresos':'sum', 'Habilitadas':'sum'}).reset_index().sort_values('Total_Ingresos', ascending=False)
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=df_g['Tienda'], y=df_g['Total_Ingresos'], name="Ingresos", marker_color='#1F497D'))
    fig2.add_trace(go.Bar(x=df_g['Tienda'], y=df_g['Habilitadas'], name="Habilitado", marker_color='#E6007E'))
    st.plotly_chart(fig2, use_container_width=True)

else:
    st.info("Esperando datos... Asegúrate de que el Google Sheet sea público y tenga pestañas con nombre 'Sem XX'.")
