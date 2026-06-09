import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuración de página
st.set_page_config(page_title="Price Shoes - Operaciones Ropa", layout="wide", page_icon="👚")

# Estilos Visuales (Magenta y Azul Marino)
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

@st.cache_data(ttl=600)
def get_operational_data():
    URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSV6dtosg0Ydt0o3NMFezC--NjHfEW82onFeY2JR4PTYD3ylG4ZlRaQBquscFrCy_Lysrau9zTW6dkn/pub?output=csv"
    
    try:
        # Cargamos el CSV sin cabeceras para procesar manualmente
        df_raw = pd.read_csv(URL, header=None )
        data_rows = []
        current_date = "Sin Fecha"
        tiendas = ['Vallejo', 'Arco Norte', 'Puebla Sur', 'Miravalle']
        
        for i, row in df_raw.iterrows():
            val = str(row[1]).strip()
            # Detectar fila de fecha (ej: "lunes, mayo 04, 2026")
            if '2026' in val and ',' in val:
                current_date = val
                continue
            # Detectar fila de tienda
            if val in tiendas:
                data_rows.append({
                    'Fecha': current_date,
                    'Tienda': val,
                    'Sis_Aduana': row[2],
                    'Muertos': row[4],
                    'Cajas': row[5],
                    'Meta_Rec': row[7],
                    'Real_Rec': row[8],
                    'Habilitadas': row[10],
                    'Ubicadas': row[11]
                })

        df = pd.DataFrame(data_rows)
        
        # Limpieza de números (quitar comas, convertir a float)
        def clean(x):
            try: return float(str(x).replace(',', '').replace('%', '').strip())
            except: return 0.0

        for col in ['Sis_Aduana', 'Muertos', 'Cajas', 'Meta_Rec', 'Real_Rec', 'Habilitadas', 'Ubicadas']:
            df[col] = df[col].apply(clean)
        
        df['Total_Ingresos'] = df['Sis_Aduana'] + df['Muertos'] + df['Cajas']
        
        # Asignación manual de semanas para el reporte
        def asignar_semana(f):
            if 'mayo 04' in f or 'mayo 10' in f: return "Semana 19"
            if 'mayo 11' in f or 'mayo 17' in f: return "Semana 20"
            if 'mayo 18' in f or 'mayo 24' in f: return "Semana 21"
            if 'mayo 25' in f or 'mayo 31' in f: return "Semana 22"
            if 'junio 01' in f or 'junio 07' in f: return "Semana 23"
            return "Semana Actual"
            
        df['Semana'] = df['Fecha'].apply(asignar_semana)
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

df = get_operational_data()

# Títulos
st.markdown('<p class="main-title">👚 PRICE SHOES • Operaciones Ropa</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">DASHBOARD DE RECUPERACIÓN AUTOMATIZADO</p>', unsafe_allow_html=True)

if not df.empty:
    # Filtros en barra lateral
    sem_list = sorted(df['Semana'].unique(), reverse=True)
    sel_sem = st.sidebar.selectbox("Semana Operativa:", sem_list)
    sel_tienda = st.sidebar.selectbox("Tienda:", ["Todas"] + sorted(df['Tienda'].unique()))
    
    df_f = df[df['Semana'] == sel_sem]
    if sel_tienda != "Todas":
        df_f = df_f[df_f['Tienda'] == sel_tienda]

    # KPIs
    st.markdown(f"### 📊 Resumen {sel_sem}")
    c1, c2, c3, c4 = st.columns(4)
    ing = df_f['Total_Ingresos'].sum()
    hab = df_f['Habilitadas'].sum()
    ubi = df_f['Ubicadas'].sum()
    rec = (df_f['Real_Rec'].sum() / df_f['Meta_Rec'].sum() * 100) if df_f['Meta_Rec'].sum() > 0 else 0
    
    c1.markdown(f'<div class="kpi-card"><p class="kpi-label">📥 INGRESOS</p><p class="kpi-value">{ing:,.0f}</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><p class="kpi-label">✨ HABILITADO</p><p class="kpi-value">{hab:,.0f} <span class="kpi-pct">({(hab/ing*100 if ing>0 else 0):.1f}%)</span></p></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><p class="kpi-label">📍 UBICADO</p><p class="kpi-value">{ubi:,.0f} <span class="kpi-pct">({(ubi/ing*100 if ing>0 else 0):.1f}%)</span></p></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-card"><p class="kpi-label">🎯 RECORRIDOS</p><p class="kpi-value">{rec:.1f}%</p></div>', unsafe_allow_html=True)

    # Gráfico
    st.markdown('<p class="graph-title">Rendimiento por Tienda</p>', unsafe_allow_html=True)
    df_g = df_f.groupby('Tienda').agg({'Total_Ingresos':'sum', 'Habilitadas':'sum'}).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_g['Tienda'], y=df_g['Total_Ingresos'], name="Ingresos", marker_color='#1F497D'))
    fig.add_trace(go.Bar(x=df_g['Tienda'], y=df_g['Habilitadas'], name="Habilitado", marker_color='#E6007E'))
    fig.update_layout(barmode='group', plot_bgcolor='white', height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Tabla
    st.markdown('<p class="graph-title">Detalle de Registros</p>', unsafe_allow_html=True)
    st.dataframe(df_f[['Fecha', 'Tienda', 'Total_Ingresos', 'Habilitadas', 'Ubicadas', 'Real_Rec']], use_container_width=True)
else:
    st.error("No se encontraron datos en el Google Sheet. Revisa el formato.")
