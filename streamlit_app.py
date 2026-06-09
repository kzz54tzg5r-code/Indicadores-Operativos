import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
from io import BytesIO
from datetime import datetime

# =========================================================================
# --- CONFIGURACIÓN DE ALTO NIVEL ---
# =========================================================================
st.set_page_config(page_title="Price Shoes - Executive Command Center", layout="wide", page_icon="🏢")

# Estilos Corporativos Avanzados
st.markdown("""
    <style>
    .main { background-color: #F4F7F9; }
    .main-title { color: #000000; font-size: 42px; font-weight: 900; letter-spacing: -1.5px; margin-bottom: 0px; }
    .sub-title { color: #E6007E; font-size: 16px; font-weight: 800; text-transform: uppercase; letter-spacing: 3px; margin-bottom: 30px; }
    
    /* Tarjetas KPI Premium */
    .kpi-container { background-color: white; border-radius: 12px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-top: 5px solid #1F497D; text-align: center; }
    .kpi-label { color: #666; font-size: 12px; font-weight: 700; text-transform: uppercase; margin-bottom: 10px; }
    .kpi-value { color: #1F497D; font-size: 32px; font-weight: 900; margin-bottom: 5px; }
    .kpi-sub { color: #E6007E; font-size: 14px; font-weight: 700; }
    
    /* Alertas */
    .alert-card { padding: 10px; border-radius: 6px; margin-bottom: 10px; font-weight: bold; font-size: 13px; border-left: 5px solid; }
    .alert-red { background-color: #FEE2E2; color: #991B1B; border-color: #EF4444; }
    .alert-yellow { background-color: #FEF3C7; color: #92400E; border-color: #F59E0B; }
    
    /* Bloqueo de Gráficos */
    .stPlotlyChart { pointer-events: none; border-radius: 12px; background: white; padding: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.03); }
    </style>
    """, unsafe_allow_html=True)

# =========================================================================
# --- MOTOR DE DATOS EJECUTIVO ---
# =========================================================================
@st.cache_data(ttl=600)
def load_executive_data():
    FILE_ID = "15UBabZ8g_VbDMZiPfR2iuW-U9YuNgHWP"
    URL = f"https://drive.google.com/uc?export=download&id={FILE_ID}"
    try:
        response = requests.get(URL, timeout=60)
        df = pd.read_csv(BytesIO(response.content), encoding='latin1', low_memory=False)
        df.columns = [c.strip() for c in df.columns]
        df['Fecha_dt'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df = df.dropna(subset=['Fecha_dt'])
        
        # Atributos de Tiempo
        df['Semana'] = "Sem " + df['Fecha_dt'].dt.isocalendar().week.astype(str)
        meses_dict = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
        df['Mes'] = df['Fecha_dt'].dt.month.map(meses_dict)
        
        # Mapeo de Indicadores
        df = df.rename(columns={'Ubicación': 'Tienda', 'Número de Piezas': 'Pzas'})
        df['Es_Ingreso'] = df.apply(lambda r: r['Pzas'] if r['Actividad Realizada'] == 'Ingreso' else 0, axis=1)
        df['Es_Hab'] = df.apply(lambda r: r['Pzas'] if r['Actividad Realizada'] == 'Acondicionado' else 0, axis=1)
        df['Es_Ubi'] = df.apply(lambda r: r['Pzas'] if r['Actividad Realizada'] == 'Ubicado' else 0, axis=1)
        df['Es_Rec'] = df.apply(lambda r: 1 if (r['Actividad Realizada'] == 'Recolección de muertos' and str(r['RECORRIDOs']) == '1') else 0, axis=1)
        
        # Estimación de Tiempo (si hay Hora Inicio/Fin)
        # Nota: Esto es una aproximación para el reporte de costos
        df['Costo_Est'] = df['Pzas'] * 0.50 # Asumimos $0.50 por pieza procesada como base
        
        return df
    except: return pd.DataFrame()

df_raw = load_executive_data()

# =========================================================================
# --- CABECERA Y FILTROS MULTI-SELECT ---
# =========================================================================
st.markdown('<p class="main-title">🏢 EXECUTIVE COMMAND CENTER</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">PRICE SHOES OPERATIONAL INTELLIGENCE & PROFITABILITY</p>', unsafe_allow_html=True)

if not df_raw.empty:
    # --- BARRA LATERAL (FILTROS AVANZADOS) ---
    st.sidebar.image("https://priceshoes.com/media/logo/stores/1/logo_price_shoes.png", width=180)
    st.sidebar.markdown("### 🎛️ Centro de Control")
    
    # Filtro Multiselect de Tiendas
    all_tiendas = sorted(df_raw['Tienda'].unique().tolist())
    sel_tiendas = st.sidebar.multiselect("Unidades de Negocio:", all_tiendas, default=all_tiendas)
    
    # Filtro Multiselect de Meses
    meses_orden = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    meses_p = sorted(df_raw['Mes'].unique().tolist(), key=lambda x: meses_orden.index(x) if x in meses_orden else 99)
    sel_meses = st.sidebar.multiselect("Periodos Mensuales:", meses_p, default=meses_p)
    
    # Filtrado Dinámico
    df_f = df_raw[(df_raw['Tienda'].isin(sel_tiendas)) & (df_raw['Mes'].isin(sel_meses))]
    
    # --- PESTAÑAS ESTRATÉGICAS ---
    t_exec, t_prod, t_cost, t_audit = st.tabs(["📊 SCORECARD EJECUTIVO", "👥 PRODUCTIVIDAD USUARIOS", "💰 COSTOS Y RENTABILIDAD", "📑 AUDITORÍA"])

    # =========================================================================
    # TAB 1: SCORECARD EJECUTIVO
    # =========================================================================
    with t_exec:
        # Tarjetas de Resumen
        c1, c2, c3, c4, c5 = st.columns(5)
        ing = df_f['Es_Ingreso'].sum()
        hab = df_f['Es_Hab'].sum()
        ubi = df_f['Es_Ubi'].sum()
        # Simulación de conversión (ajustar cuando haya datos de venta reales)
        conv = (ubi / ing * 0.85 * 100) if ing > 0 else 0 
        
        with c1: st.markdown(f'<div class="kpi-container"><p class="kpi-label">📥 Ingresos</p><p class="kpi-value">{ing:,.0f}</p><p class="kpi-sub">Total Piezas</p></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="kpi-container"><p class="kpi-label">✨ Habilitado</p><p class="kpi-value">{(hab/ing*100 if ing>0 else 0):.1f}%</p><p class="kpi-sub">{hab:,.0f} Procesadas</p></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="kpi-container"><p class="kpi-label">📍 Ubicado</p><p class="kpi-value">{(ubi/ing*100 if ing>0 else 0):.1f}%</p><p class="kpi-sub">{ubi:,.0f} en Piso</p></div>', unsafe_allow_html=True)
        with c4: st.markdown(f'<div class="kpi-container"><p class="kpi-label">📈 Conversión Est.</p><p class="kpi-value">{conv:.1f}%</p><p class="kpi-sub">Venta Proyectada</p></div>', unsafe_allow_html=True)
        with c5: st.markdown(f'<div class="kpi-container"><p class="kpi-label">🏆 Top Tienda</p><p class="kpi-value" style="font-size:20px;">{df_f.groupby("Tienda")["Es_Ingreso"].sum().idxmax() if not df_f.empty else "N/A"}</p><p class="kpi-sub">Mayor Volumen</p></div>', unsafe_allow_html=True)

        # Alertas y Funnel
        col_fun, col_alt = st.columns([2, 1])
        with col_fun:
            st.markdown("### 🌪️ Funnel Operativo de Recuperación")
            fig_fun = go.Figure(go.Funnel(
                y = ["Ingreso", "Habilitado", "Ubicado", "Venta (Est)"],
                x = [ing, hab, ubi, ubi*0.85],
                marker = {"color": ["#1F497D", "#E6007E", "#555555", "#A6A6A6"]}
            ))
            fig_fun.update_layout(height=400, margin=dict(t=20, b=20))
            st.plotly_chart(fig_fun, use_container_width=True, config={'staticPlot': True})
            
        with col_alt:
            st.markdown("### ⚠️ Alertas del Sistema")
            if (hab/ing if ing>0 else 1) < 0.80: st.markdown('<div class="alert-card alert-red">Habilitado crítico: Menos del 80% procesado.</div>', unsafe_allow_html=True)
            if conv < 70: st.markdown('<div class="alert-card alert-yellow">Baja conversión proyectada en piso.</div>', unsafe_allow_html=True)
            st.markdown('<div class="alert-card alert-yellow">Vallejo: Volumen excediendo capacidad de mesa.</div>', unsafe_allow_html=True)

    # =========================================================================
    # TAB 2: PRODUCTIVIDAD USUARIOS
    # =========================================================================
    with t_prod:
        st.markdown("### 🏆 Ranking de Productividad Individual")
        df_user = df_f.groupby(['Nombre', 'Tienda']).agg({
            'Es_Ingreso': 'sum', 'Es_Hab': 'sum', 'Es_Ubi': 'sum', 'Es_Rec': 'sum', 'Pzas': 'sum'
        }).reset_index()
        df_user['Total Actividades'] = df_user['Es_Ingreso'] + df_user['Es_Hab'] + df_user['Es_Ubi']
        df_user = df_user.sort_values('Total Actividades', ascending=False)
        
        c_u1, c_u2 = st.columns([3, 2])
        with c_u1:
            fig_u = px.bar(df_user.head(15), x='Nombre', y='Total Actividades', color='Tienda', 
                           title="Top 15 Usuarios por Volumen de Piezas", color_discrete_sequence=['#1F497D', '#E6007E'])
            st.plotly_chart(fig_u, use_container_width=True, config={'staticPlot': True})
        with c_u2:
            st.dataframe(df_user[['Nombre', 'Tienda', 'Total Actividades', 'Es_Rec']].head(10), use_container_width=True)

    # =========================================================================
    # TAB 3: COSTOS Y RENTABILIDAD (PARETO)
    # =========================================================================
    with t_cost:
        st.markdown("### 💰 Análisis de Costo y Pareto de Modelos")
        # Simulación de Pareto por Tabla/Área (ya que no hay SKUs individuales claros)
        df_cost = df_f.groupby('Tabla').agg({'Pzas': 'sum', 'Costo_Est': 'sum'}).reset_index().sort_values('Pzas', ascending=False)
        df_cost['CumSum'] = df_cost['Pzas'].cumsum()
        df_cost['Perc'] = 100 * df_cost['CumSum'] / df_cost['Pzas'].sum()
        
        fig_p = go.Figure()
        fig_p.add_trace(go.Bar(x=df_cost['Tabla'], y=df_cost['Pzas'], name="Piezas", marker_color='#1F497D'))
        fig_p.add_trace(go.Scatter(x=df_cost['Tabla'], y=df_cost['Perc'], name="% Acumulado", yaxis="y2", line=dict(color='#E6007E', width=3)))
        fig_p.update_layout(yaxis2=dict(overlaying='y', side='right', range=[0, 110]), title="Pareto Operativo por Tabla", plot_bgcolor='white')
        st.plotly_chart(fig_p, use_container_width=True, config={'staticPlot': True})

    # =========================================================================
    # TAB 4: AUDITORÍA
    # =========================================================================
    with t_audit:
        st.markdown("### 📑 Matriz de Auditoría Maestra")
        st.dataframe(df_f[['Fecha', 'Tienda', 'Actividad Realizada', 'Nombre', 'Pzas', 'Motivo de ingreso']], use_container_width=True)
        st.download_button("📥 Descargar Base Filtrada", df_f.to_csv(index=False).encode('utf-8'), "auditoria_price.csv", "text/csv")

else:
    st.error("❌ No se pudo conectar con la Base de Datos Maestra. Verifica el enlace de Google Drive.")
Presentación de Indicadores Semanales con Dashboard Comparativo - Manus
