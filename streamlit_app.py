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
    # URL de descarga directa para Google Sheets publicados como XLSX
    # IMPORTANTE: El usuario debe haber publicado "Todo el documento" como "Microsoft Excel (.xlsx)"
    URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSV6dtosg0Ydt0o3NMFezC--NjHfEW82onFeY2JR4PTYD3ylG4ZlRaQBquscFrCy_Lysrau9zTW6dkn/pub?output=xlsx"
    
    try:
        response = requests.get(URL, timeout=30)
        response.raise_for_status()
        
        # Cargar el archivo Excel completo
        xls = pd.ExcelFile(BytesIO(response.content), engine='openpyxl')
        
        data_rows = []
        # Lista de tiendas a buscar en las hojas
        tiendas_objetivo = ['Vallejo', 'Arco Norte', 'Puebla Sur', 'Miravalle', 'Ecatepec']
        
        for sheet_name in xls.sheet_names:
            # Procesar solo pestañas que parezcan semanas (Sem 20, Sem 21, etc.)
            if not sheet_name.lower().strip().startswith('sem'):
                continue
                
            # Leer la hoja completa
            df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None, engine='openpyxl')
            current_date = "Sin Fecha"
            
            for i, row in df_raw.iterrows():
                if len(row) < 2: continue
                val = str(row[1]).strip()
                
                # Identificar fila de fecha
                if '2026' in val and ',' in val:
                    current_date = val
                    continue
                
                # Identificar fila de tienda
                if any(t.lower() in val.lower() for t in tiendas_objetivo) and len(val) < 30:
                    try:
                        # Extraer mes del nombre de la fecha
                        mes_ext = 'Mayo' if 'mayo' in current_date.lower() else ('Junio' if 'junio' in current_date.lower() else 'Julio-Dic')
                        
                        data_rows.append({
                            'Mes': mes_ext,
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
                    except Exception:
                        continue

        if not data_rows:
            return pd.DataFrame()
            
        df = pd.DataFrame(data_rows)
        
        # Limpiar y convertir a números
        def clean_num(x):
            try:
                if pd.isna(x): return 0.0
                s = str(x).replace(',', '').replace('%', '').strip()
                return float(s)
            except:
                return 0.0

        for col in ['Sis_Aduana', 'Muertos', 'Cajas', 'Meta_Rec', 'Real_Rec', 'Habilitadas', 'Ubicadas']:
            df[col] = df[col].apply(clean_num)
        
        df['Total_Ingresos'] = df['Sis_Aduana'] + df['Muertos'] + df['Cajas']
        return df
        
    except Exception as e:
        st.error(f"Error al cargar datos del Excel: {e}")
        return pd.DataFrame()

# =========================================================================
# --- LÓGICA DE INTERFAZ ---
# =========================================================================
df = load_all_data()

st.markdown('<p class="main-title">👚 PRICE SHOES • Operaciones Ropa</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">DASHBOARD ANUAL CONSOLIDADO</p>', unsafe_allow_html=True)

if not df.empty:
    st.sidebar.markdown("### 🔍 Filtros de Reporte")
    
    # Filtro Mes
    meses = ["Todos"] + sorted(df['Mes'].unique().tolist())
    sel_mes = st.sidebar.selectbox("Selecciona Mes:", meses)
    df_mes = df if sel_mes == "Todos" else df[df['Mes'] == sel_mes]
    
    # Filtro Semana
    semanas = ["Todas"] + sorted(df_mes['Semana'].unique().tolist(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    sel_sem = st.sidebar.selectbox("Selecciona Semana:", semanas)
    
    # Filtro Tienda
    tiendas = ["Todas"] + sorted(df['Tienda'].unique().tolist())
    sel_tienda = st.sidebar.selectbox("Selecciona Tienda:", tiendas)

    # Aplicar filtros
    df_f = df_mes.copy()
    if sel_sem != "Todas": df_f = df_f[df_f['Semana'] == sel_sem]
    if sel_tienda != "Todas": df_f = df_f[df_f['Tienda'] == sel_tienda]

    # Visualización de KPIs
    st.markdown(f"### 📊 Reporte: {sel_mes} / {sel_sem} / {sel_tienda}")
    
    c1, c2, c3, c4 = st.columns(4)
    ing, hab, ubi = df_f['Total_Ingresos'].sum(), df_f['Habilitadas'].sum(), df_f['Ubicadas'].sum()
    met, rea = df_f['Meta_Rec'].sum(), df_f['Real_Rec'].sum()
    
    c1.markdown(f'<div class="kpi-card"><p class="kpi-label">📥 INGRESOS</p><p class="kpi-value">{ing:,.0f}</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><p class="kpi-label">✨ HABILITADO</p><p class="kpi-value">{hab:,.0f} <small class="kpi-pct">({(hab/ing*100 if ing>0 else 0):.1f}%)</small></p></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><p class="kpi-label">📍 UBICADO</p><p class="kpi-value">{ubi:,.0f} <small class="kpi-pct">({(ubi/ing*100 if ing>0 else 0):.1f}%)</small></p></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-card"><p class="kpi-label">🎯 RECORRIDOS</p><p class="kpi-value">{(rea/met*100 if met>0 else 0):.1f}%</p></div>', unsafe_allow_html=True)

    # Gráfico de Evolución
    if sel_sem == "Todas":
        st.markdown('<p class="graph-title">Tendencia Semanal de Operación</p>', unsafe_allow_html=True)
        df_t = df_f.groupby('Semana').agg({'Total_Ingresos':'sum', 'Habilitadas':'sum'}).reset_index()
        df_t['orden'] = df_t['Semana'].apply(lambda x: int(''.join(filter(str.isdigit, x)) or 0))
        df_t = df_t.sort_values('orden')
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_t['Semana'], y=df_t['Total_Ingresos'], name="Ingresos", line=dict(color='#1F497D', width=3)))
        fig.add_trace(go.Scatter(x=df_t['Semana'], y=df_t['Habilitadas'], name="Habilitado", line=dict(color='#E6007E', width=3)))
        fig.update_layout(plot_bgcolor='white', height=400, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    # Ranking por Tienda
    st.markdown('<p class="graph-title">Comparativo por Sucursal</p>', unsafe_allow_html=True)
    df_g = df_f.groupby('Tienda').agg({'Total_Ingresos':'sum', 'Habilitadas':'sum'}).reset_index().sort_values('Total_Ingresos', ascending=False)
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=df_g['Tienda'], y=df_g['Total_Ingresos'], name="Ingresos", marker_color='#1F497D'))
    fig2.add_trace(go.Bar(x=df_g['Tienda'], y=df_g['Habilitadas'], name="Habilitado", marker_color='#E6007E'))
    fig2.update_layout(barmode='group', plot_bgcolor='white', height=400)
    st.plotly_chart(fig2, use_container_width=True)

    # Matriz Detallada
    with st.expander("Ver Matriz de Datos Detallada"):
        st.dataframe(df_f.groupby(['Mes', 'Semana', 'Tienda']).agg({
            'Total_Ingresos': 'sum',
            'Habilitadas': 'sum',
            'Ubicadas': 'sum',
            'Real_Rec': 'sum',
            'Meta_Rec': 'sum'
        }).reset_index(), use_container_width=True)

else:
    st.info("No se detectaron datos. Por favor, asegúrate de publicar el Google Sheet como Excel (.xlsx) y seleccionar 'Todo el documento'.")
