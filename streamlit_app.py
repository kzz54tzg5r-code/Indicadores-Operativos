import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
from io import BytesIO

# =========================================================================
# --- CONFIGURACIÓN EJECUTIVA ---
# =========================================================================
st.set_page_config(page_title="Price Shoes - Operational Intelligence", layout="wide", page_icon="🏢")

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
    .stPlotlyChart { pointer-events: none; border-radius: 12px; background: white; padding: 10px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_data():
    URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSV6dtosg0Ydt0o3NMFezC--NjHfEW82onFeY2JR4PTYD3ylG4ZlRaQBquscFrCy_Lysrau9zTW6dkn/pub?output=xlsx"
    try:
        response = requests.get(URL, timeout=60)
        xls = pd.ExcelFile(BytesIO(response.content), engine='openpyxl')
        
        df_muertos = pd.DataFrame()
        df_venta = pd.DataFrame()
        
        for sheet in xls.sheet_names:
            if 'muertos' in sheet.lower():
                df_muertos = pd.read_excel(xls, sheet_name=sheet, engine='openpyxl')
            if 'venta' in sheet.lower() or 'devolucion' in sheet.lower():
                df_venta = pd.read_excel(xls, sheet_name=sheet, engine='openpyxl')

        df_muertos.columns = [c.strip() for c in df_muertos.columns]
        df_muertos['Fecha_dt'] = pd.to_datetime(df_muertos['Fecha'], errors='coerce')
        df_muertos = df_muertos.dropna(subset=['Fecha_dt'])
        
        # --- LÓGICA DE INGRESOS ---
        motivos_ingreso = ['Cajas', 'Muertos', 'Probador']
        df_muertos['Ingreso_Recoleccion'] = df_muertos.apply(
            lambda r: r['Número de Piezas'] if (str(r['Actividad Realizada']).strip() == 'Recolección de muertos' and 
                                               str(r['Motivo de ingreso']).strip() in motivos_ingreso) else 0, axis=1
        )
        
        # --- LÓGICA DE RECORRIDOS (METAS DINÁMICAS) ---
        # Lunes=0, Martes=1, Miercoles=2 (Meta 5) | Jueves=3, Viernes=4, Sabado=5, Domingo=6 (Meta 8)
        df_muertos['Dia_Semana'] = df_muertos['Fecha_dt'].dt.dayofweek
        df_muertos['Meta_Rec_Dia'] = df_muertos['Dia_Semana'].apply(lambda x: 5 if x <= 2 else 8)
        
        # Solo contabilizamos recorridos cuando RECORRIDOs == 1
        df_muertos['Real_Rec'] = df_muertos['RECORRIDOs'].apply(lambda x: 1 if str(x) == '1' else 0)

        # Devoluciones
        ingreso_devoluciones = 0
        if not df_venta.empty:
            df_venta.columns = [c.strip() for c in df_venta.columns]
            col_dev = [c for c in df_venta.columns if 'devolucion' in c.lower()]
            if col_dev: ingreso_devoluciones = df_venta[col_dev[0]].sum()

        # Enriquecer
        df_muertos['Semana'] = "Sem " + df_muertos['Fecha_dt'].dt.isocalendar().week.astype(str)
        m_dict = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
        df_muertos['Mes'] = df_muertos['Fecha_dt'].dt.month.map(m_dict)
        df_muertos = df_muertos.rename(columns={'Ubicación': 'Tienda', 'Número de Piezas': 'Pzas'})
        
        df_muertos['Es_Hab'] = df_muertos.apply(lambda r: r['Pzas'] if str(r['Actividad Realizada']).strip() == 'Acondicionado' else 0, axis=1)
        df_muertos['Es_Ubi'] = df_muertos.apply(lambda r: r['Pzas'] if str(r['Actividad Realizada']).strip() == 'Ubicado' else 0, axis=1)
        
        return df_muertos, ingreso_devoluciones
    except Exception as e:
        st.error(f"Error de carga: {e}")
        return pd.DataFrame(), 0

df_raw, dev_total = load_data()

if not df_raw.empty:
    st.sidebar.image("https://priceshoes.com/media/logo/stores/1/logo_price_shoes.png", width=160)
    sel_tiendas = st.sidebar.multiselect("Tiendas:", sorted(df_raw['Tienda'].unique().tolist()), default=df_raw['Tienda'].unique().tolist())
    sel_meses = st.sidebar.multiselect("Meses:", ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'], default=df_raw['Mes'].unique().tolist())
    actividades = sorted(df_raw['Actividad Realizada'].dropna().unique().tolist())
    sel_actividades = st.sidebar.multiselect("Actividades:", actividades, default=actividades)
    
    df_f = df_raw[(df_raw['Tienda'].isin(sel_tiendas)) & (df_raw['Mes'].isin(sel_meses)) & (df_raw['Actividad Realizada'].isin(sel_actividades))]
    
    st.markdown('<p class="main-title">PRICE SHOES • Operational Intelligence</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">SISTEMA DE CONTROL DE RECUPERACIÓN Y RECORRIDOS</p>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📊 DASHBOARD EJECUTIVO", "👥 PRODUCTIVIDAD", "📑 AUDITORÍA"])

    with tab1:
        # Cálculos de Recorridos (Agrupado por Fecha y Tienda para comparar contra meta diaria)
        df_rec_daily = df_f.groupby(['Fecha_dt', 'Tienda', 'Meta_Rec_Dia']).agg({'Real_Rec': 'sum'}).reset_index()
        total_meta = df_rec_daily['Meta_Rec_Dia'].sum()
        total_real = df_rec_daily['Real_Rec'].sum()
        pct_rec_total = (total_real / total_meta * 100) if total_meta > 0 else 0

        ing_total = df_f['Ingreso_Recoleccion'].sum() + dev_total
        hab = df_f['Es_Hab'].sum()
        ubi = df_f['Es_Ubi'].sum()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="kpi-container"><p class="kpi-label">📥 Ingresos Totales</p><p class="kpi-value">{ing_total:,.0f}</p></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="kpi-container"><p class="kpi-label">✨ Habilitado</p><p class="kpi-value">{(hab/ing_total*100 if ing_total>0 else 0):.1f}%</p></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="kpi-container"><p class="kpi-label">📍 Ubicado</p><p class="kpi-value">{(ubi/ing_total*100 if ing_total>0 else 0):.1f}%</p></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="kpi-container"><p class="kpi-label">🎯 Efic. Recorridos</p><p class="kpi-value">{pct_rec_total:.1f}%</p><p class="kpi-sub">{total_real:,.0f} de {total_meta:,.0f}</p></div>', unsafe_allow_html=True)

        col_fun, col_alt = st.columns([2, 1])
        with col_fun:
            fig = px.funnel(x=[ing_total, hab, ubi], y=["Ingreso Total", "Habilitado", "Ubicado"], color_discrete_sequence=['#1F497D'])
            fig.update_layout(height=400, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})
        with col_alt:
            st.markdown("### ⚠️ Alertas")
            if pct_rec_total < 90: st.markdown(f'<div class="alert-card alert-red">Cumplimiento de recorridos crítico: {pct_rec_total:.1f}%</div>', unsafe_allow_html=True)
            if (hab/ing_total if ing_total>0 else 1) < 0.8: st.markdown('<div class="alert-card alert-yellow">Habilitado bajo el 80%</div>', unsafe_allow_html=True)

    with tab2:
        df_u = df_f.groupby(['Nombre', 'Tienda']).agg({'Pzas':'sum'}).reset_index().sort_values('Pzas', ascending=False)
        st.plotly_chart(px.bar(df_u.head(15), x='Nombre', y='Pzas', color='Tienda', title="Ranking de Actividad por Usuario"), use_container_width=True, config={'staticPlot': True})
        st.dataframe(df_u.head(20), use_container_width=True)

    with tab3:
        st.dataframe(df_f[['Fecha', 'Tienda', 'Actividad Realizada', 'Nombre', 'Pzas', 'Motivo de ingreso', 'Real_Rec']], use_container_width=True)
else:
    st.error("Error al conectar con la Base de Datos. Verifica las pestañas.")
