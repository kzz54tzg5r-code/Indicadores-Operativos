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
    
    /* Estilos para las tarjetas de resumen macro */
    .macro-card-header { background-color: #1F497D; color: white; text-align: center; padding: 8px; border-radius: 4px 4px 0 0; font-weight: bold; font-size: 14px; margin-bottom: 0; }
    .macro-card-body { background-color: #F8F9FA; border: 1px solid #D9D9D9; border-top: none; border-radius: 0 0 4px 4px; padding: 12px; text-align: center; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .macro-label { color: #555555; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-bottom: 2px; }
    .macro-value { color: #1F497D; font-size: 18px; font-weight: bold; margin-bottom: 0; }
    .macro-pct { color: #E6007E; font-size: 14px; font-weight: bold; }
    .macro-divider { border-top: 1px dashed #D9D9D9; margin: 8px 0; }
    
    .kpi-card { background-color: #F8F9FA; border: 1px solid #D9D9D9; border-radius: 4px; padding: 15px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# =========================================================================
# --- MOTOR DE CARGA MULTI-PESTAÑA (EXCEL) ---
# =========================================================================
@st.cache_data(ttl=600)
def load_all_data():
    URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSV6dtosg0Ydt0o3NMFezC--NjHfEW82onFeY2JR4PTYD3ylG4ZlRaQBquscFrCy_Lysrau9zTW6dkn/pub?output=xlsx"
    
    try:
        response = requests.get(URL, timeout=30)
        response.raise_for_status()
        xls = pd.ExcelFile(BytesIO(response.content), engine='openpyxl')
        
        data_rows = []
        tiendas_objetivo = ['Vallejo', 'Arco Norte', 'Puebla Sur', 'Miravalle', 'Ecatepec']
        
        for sheet_name in xls.sheet_names:
            if not sheet_name.lower().strip().startswith('sem'): continue
            df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None, engine='openpyxl')
            current_date = "Sin Fecha"
            
            for i, row in df_raw.iterrows():
                if len(row) < 2: continue
                val = str(row[1]).strip()
                if '2026' in val and ',' in val:
                    current_date = val
                    continue
                if any(t.lower() in val.lower() for t in tiendas_objetivo) and len(val) < 30:
                    try:
                        mes_ext = 'Mayo' if 'mayo' in current_date.lower() else ('Junio' if 'junio' in current_date.lower() else 'Julio-Dic')
                        data_rows.append({
                            'Mes': mes_ext,
                            'Semana': sheet_name.strip(),
                            'Tienda': val,
                            'Sis_Aduana': row[2], 'Muertos': row[4], 'Cajas': row[5],
                            'Meta_Rec': row[7], 'Real_Rec': row[8],
                            'Habilitadas': row[10], 'Ubicadas': row[11]
                        })
                    except Exception: continue

        if not data_rows: return pd.DataFrame()
        df = pd.DataFrame(data_rows)
        def clean_num(x):
            try: return float(str(x).replace(',', '').replace('%', '').strip())
            except: return 0.0
        for col in ['Sis_Aduana', 'Muertos', 'Cajas', 'Meta_Rec', 'Real_Rec', 'Habilitadas', 'Ubicadas']:
            df[col] = df[col].apply(clean_num)
        df['Total_Ingresos'] = df['Sis_Aduana'] + df['Muertos'] + df['Cajas']
        return df
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return pd.DataFrame()

# =========================================================================
# --- LÓGICA DE INTERFAZ ---
# =========================================================================
df = load_all_data()

st.markdown('<p class="main-title">👚 PRICE SHOES • Operaciones Ropa</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">DASHBOARD ANUAL CONSOLIDADO</p>', unsafe_allow_html=True)

if not df.empty:
    # --- RESUMEN MACRO (ÚLTIMAS 4 SEMANAS) ---
    st.markdown('<p class="graph-title">📊 Resumen Macro Operativo (Últimas 4 Semanas)</p>', unsafe_allow_html=True)
    
    # Obtener las últimas 4 semanas ordenadas
    all_weeks_sorted = sorted(df['Semana'].unique().tolist(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    last_4_weeks = all_weeks_sorted[-4:]
    
    cols_macro = st.columns(4)
    for i, sem in enumerate(last_4_weeks):
        df_sem = df[df['Semana'] == sem]
        ing = df_sem['Total_Ingresos'].sum()
        hab = df_sem['Habilitadas'].sum()
        ubi = df_sem['Ubicadas'].sum()
        met = df_sem['Meta_Rec'].sum()
        rea = df_sem['Real_Rec'].sum()
        
        pct_hab = (hab/ing*100) if ing > 0 else 0
        pct_ubi = (ubi/ing*100) if ing > 0 else 0
        pct_rec = (rea/met*100) if met > 0 else 0
        
        with cols_macro[i]:
            st.markdown(f'<div class="macro-card-header">{sem}</div>', unsafe_allow_html=True)
            st.markdown(f"""
                <div class="macro-card-body">
                    <p class="macro-label">📥 Ingresos</p><p class="macro-value">{ing:,.0f}</p>
                    <div class="macro-divider"></div>
                    <p class="macro-label">✨ Habilitado</p><p class="macro-value">{hab:,.0f} <span class="macro-pct">({pct_hab:.1f}%)</span></p>
                    <div class="macro-divider"></div>
                    <p class="macro-label">📍 Ubicado</p><p class="macro-value">{ubi:,.0f} <span class="macro-pct">({pct_ubi:.1f}%)</span></p>
                    <div class="macro-divider"></div>
                    <p class="macro-label">🎯 % Recorridos</p><p class="macro-value">{pct_rec:.1f}%</p>
                </div>
            """, unsafe_allow_html=True)

    # --- FILTROS DE REPORTE ---
    st.sidebar.markdown("### 🔍 Filtros Detallados")
    sel_mes = st.sidebar.selectbox("Mes:", ["Todos"] + sorted(df['Mes'].unique().tolist()))
    df_mes = df if sel_mes == "Todos" else df[df['Mes'] == sel_mes]
    sel_sem = st.sidebar.selectbox("Semana:", ["Todas"] + sorted(df_mes['Semana'].unique().tolist(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0)))
    sel_tienda = st.sidebar.selectbox("Tienda:", ["Todas"] + sorted(df['Tienda'].unique().tolist()))

    df_f = df_mes.copy()
    if sel_sem != "Todas": df_f = df_f[df_f['Semana'] == sel_sem]
    if sel_tienda != "Todas": df_f = df_f[df_f['Tienda'] == sel_tienda]

    # Visualización Detallada
    st.markdown(f"### 📈 Detalle: {sel_mes} / {sel_sem} / {sel_tienda}")
    
    # Gráficos
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<p class="graph-title">Ingresos vs Habilitado por Tienda</p>', unsafe_allow_html=True)
        df_g = df_f.groupby('Tienda').agg({'Total_Ingresos':'sum', 'Habilitadas':'sum'}).reset_index().sort_values('Total_Ingresos', ascending=False)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_g['Tienda'], y=df_g['Total_Ingresos'], name="Ingresos", marker_color='#1F497D'))
        fig.add_trace(go.Bar(x=df_g['Tienda'], y=df_g['Habilitadas'], name="Habilitado", marker_color='#E6007E'))
        fig.update_layout(barmode='group', plot_bgcolor='white', height=350, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.markdown('<p class="graph-title">Cumplimiento de Recorridos (%)</p>', unsafe_allow_html=True)
        df_r = df_f.groupby('Tienda').agg({'Real_Rec':'sum', 'Meta_Rec':'sum'}).reset_index()
        df_r['% Recorridos'] = (df_r['Real_Rec'] / df_r['Meta_Rec'] * 100).fillna(0)
        fig2 = go.Figure(go.Bar(x=df_r['Tienda'], y=df_r['% Recorridos'], marker_color='#1F497D', text=df_r['% Recorridos'].map('{:.1f}%'.format), textposition='auto'))
        fig2.update_layout(plot_bgcolor='white', height=350, margin=dict(t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    # Tabla
    with st.expander("Ver Matriz de Datos"):
        st.dataframe(df_f.groupby(['Mes', 'Semana', 'Tienda']).agg({'Total_Ingresos': 'sum', 'Habilitadas': 'sum', 'Ubicadas': 'sum', 'Real_Rec': 'sum', 'Meta_Rec': 'sum'}).reset_index(), use_container_width=True)
else:
    st.info("Esperando datos... Asegúrate de publicar el Google Sheet como Excel (.xlsx) y seleccionar 'Todo el documento'.")
