import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
from io import BytesIO

# =========================================================================
# --- CONFIGURACIÓN EJECUTIVA ---
# =========================================================================
st.set_page_config(page_title="Price Shoes - Executive Command Center", layout="wide", page_icon="🏢")

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
    URL = "https://drive.google.com/uc?export=download&id=15UBabZ8g_VbDMZiPfR2iuW-U9YuNgHWP"
    try:
        response = requests.get(URL, timeout=60)
        df = pd.read_csv(BytesIO(response.content), encoding='latin1', low_memory=False)
        df.columns = [c.strip() for c in df.columns]
        df['Fecha_dt'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df = df.dropna(subset=['Fecha_dt'])
        df['Semana'] = "Sem " + df['Fecha_dt'].dt.isocalendar().week.astype(str)
        m_dict = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
        df['Mes'] = df['Fecha_dt'].dt.month.map(m_dict)
        df = df.rename(columns={'Ubicación': 'Tienda', 'Número de Piezas': 'Pzas'})
        df['Es_Ingreso'] = df.apply(lambda r: r['Pzas'] if r['Actividad Realizada'] == 'Ingreso' else 0, axis=1)
        df['Es_Hab'] = df.apply(lambda r: r['Pzas'] if r['Actividad Realizada'] == 'Acondicionado' else 0, axis=1)
        df['Es_Ubi'] = df.apply(lambda r: r['Pzas'] if r['Actividad Realizada'] == 'Ubicado' else 0, axis=1)
        df['Es_Rec'] = df.apply(lambda r: 1 if (r['Actividad Realizada'] == 'Recolección de muertos' and str(r['RECORRIDOs']) == '1') else 0, axis=1)
        return df
    except: return pd.DataFrame()

df_raw = load_data()

if not df_raw.empty:
    st.sidebar.image("https://priceshoes.com/media/logo/stores/1/logo_price_shoes.png", width=160)
    sel_tiendas = st.sidebar.multiselect("Tiendas:", sorted(df_raw['Tienda'].unique().tolist()), default=df_raw['Tienda'].unique().tolist())
    sel_meses = st.sidebar.multiselect("Meses:", ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'], default=df_raw['Mes'].unique().tolist())
    
    df_f = df_raw[(df_raw['Tienda'].isin(sel_tiendas)) & (df_raw['Mes'].isin(sel_meses))]
    
    st.markdown('<p class="main-title">PRICE SHOES • Executive Command</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">OPERATIONAL INTELLIGENCE SYSTEM</p>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📊 DASHBOARD", "👥 PRODUCTIVIDAD", "📑 AUDITORÍA"])

    with tab1:
        ing, hab, ubi = df_f['Es_Ingreso'].sum(), df_f['Es_Hab'].sum(), df_f['Es_Ubi'].sum()
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="kpi-container"><p class="kpi-label">📥 Ingresos</p><p class="kpi-value">{ing:,.0f}</p></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="kpi-container"><p class="kpi-label">✨ Habilitado</p><p class="kpi-value">{(hab/ing*100 if ing>0 else 0):.1f}%</p></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="kpi-container"><p class="kpi-label">📍 Ubicado</p><p class="kpi-value">{(ubi/ing*100 if ing>0 else 0):.1f}%</p></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="kpi-container"><p class="kpi-label">🎯 Recorridos</p><p class="kpi-value">{df_f["Es_Rec"].sum():,.0f}</p></div>', unsafe_allow_html=True)

        col_a, col_b = st.columns([2, 1])
        with col_a:
            fig = px.funnel(x=[ing, hab, ubi], y=["Ingreso", "Habilitado", "Ubicado"], color_discrete_sequence=['#1F497D'])
            fig.update_layout(height=400, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})
        with col_b:
            st.markdown("### ⚠️ Alertas")
            if (hab/ing if ing>0 else 1) < 0.8: st.markdown('<div class="alert-card alert-red">Habilitado bajo el 80%</div>', unsafe_allow_html=True)
            st.markdown('<div class="alert-card alert-yellow">Volumen alto en Vallejo</div>', unsafe_allow_html=True)

    with tab2:
        df_u = df_f.groupby(['Nombre', 'Tienda']).agg({'Pzas':'sum'}).reset_index().sort_values('Pzas', ascending=False)
        st.plotly_chart(px.bar(df_u.head(15), x='Nombre', y='Pzas', color='Tienda', title="Top Productividad"), use_container_width=True, config={'staticPlot': True})
        st.dataframe(df_u.head(20), use_container_width=True)

    with tab3:
        st.dataframe(df_f[['Fecha', 'Tienda', 'Actividad Realizada', 'Nombre', 'Pzas']], use_container_width=True)
else:
    st.error("Error al conectar con la Base de Datos.")
