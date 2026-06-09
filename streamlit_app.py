import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
from io import BytesIO
from datetime import datetime

# =========================================================================
# --- CONFIGURACIÓN DE NIVEL BI DIRECTOR ---
# =========================================================================
st.set_page_config(page_title="Price Shoes BI - Command Center", layout="wide", page_icon="📈")

# Estilos Corporativos Premium
st.markdown("""
    <style>
    .main { background-color: #F8F9FB; }
    .main-title { color: #1F497D; font-size: 40px; font-weight: 900; letter-spacing: -1.5px; margin-bottom: 0px; }
    .sub-title { color: #E6007E; font-size: 14px; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 30px; }
    
    /* KPI Cards */
    .kpi-card { background-color: white; border-radius: 12px; padding: 22px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); border-top: 6px solid #1F497D; text-align: center; }
    .kpi-label { color: #666; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 10px; }
    .kpi-value { color: #1F497D; font-size: 30px; font-weight: 900; margin-bottom: 5px; }
    .kpi-trend { font-size: 13px; font-weight: 800; }
    
    /* Alertas Ejecutivas */
    .exec-alert { padding: 12px; border-radius: 8px; margin-bottom: 12px; font-weight: bold; font-size: 13px; border-left: 6px solid; }
    .alert-critical { background-color: #FEE2E2; color: #991B1B; border-color: #EF4444; }
    .alert-warning { background-color: #FEF3C7; color: #92400E; border-color: #F59E0B; }
    
    /* Tabs & Tables */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #F1F3F5; border-radius: 6px 6px 0 0; padding: 10px 20px; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #1F497D !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_master_bi_data():
    URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSV6dtosg0Ydt0o3NMFezC--NjHfEW82onFeY2JR4PTYD3ylG4ZlRaQBquscFrCy_Lysrau9zTW6dkn/pub?output=xlsx"
    try:
        response = requests.get(URL, timeout=30)
        xls = pd.ExcelFile(BytesIO(response.content), engine='openpyxl')
        
        all_data = []
        for sheet in xls.sheet_names:
            if 'sem' in sheet.lower():
                df_raw = pd.read_excel(xls, sheet_name=sheet, header=None, engine='openpyxl')
                header_rows = df_raw[df_raw[1] == 'Tienda'].index.tolist()
                
                for h_idx in header_rows:
                    fecha_val = df_raw.iloc[h_idx-1, 1]
                    if not isinstance(fecha_val, datetime): continue
                    
                    d_idx = h_idx + 1
                    while d_idx < len(df_raw) and pd.notna(df_raw.iloc[d_idx, 1]):
                        row = df_raw.iloc[d_idx, 1:15].tolist()
                        all_data.append({
                            'Tienda': row[0], 'Ing_Aduana_Sis': row[1], 'Ing_Aduana': row[2], 
                            'Ing_Muertos': row[3], 'Ing_Cajas': row[4], 'Total_Ing': row[5],
                            'Meta_Rec': row[6], 'Real_Rec': row[7], 'Pzas_Rec': row[8],
                            'Pzas_Hab': row[9], 'Pzas_Ubi': row[10], 'Fecha': fecha_val, 'Semana': sheet
                        })
                        d_idx += 1
        
        df = pd.DataFrame(all_data)
        for c in ['Total_Ing', 'Meta_Rec', 'Real_Rec', 'Pzas_Rec', 'Pzas_Hab', 'Pzas_Ubi']:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
        # --- LÓGICA DE BI ESTRATÉGICO ---
        # 1. Conversión a Venta (Simulada al 85% del Ubicado según regla ejecutiva)
        df['Venta_Est'] = df['Pzas_Ubi'] * 0.85
        df['Valor_Rec_Est'] = df['Venta_Est'] * 350 # Precio promedio estimado $350
        df['Costo_Rec_Est'] = df['Pzas_Hab'] * 2.50 # Costo operativo est. $2.50 por pza
        
        meses = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
        df['Mes'] = df['Fecha'].dt.month.map(meses)
        
        return df
    except Exception as e:
        st.error(f"Error de Conexión BI: {e}")
        return pd.DataFrame()

df_raw = load_master_bi_data()

# =========================================================================
# --- CENTRO DE MANDO EJECUTIVO ---
# =========================================================================
if not df_raw.empty:
    # Sidebar Corporativo
    st.sidebar.image("https://priceshoes.com/media/logo/stores/1/logo_price_shoes.png", width=160)
    st.sidebar.markdown("### 🎛️ Filtros Estratégicos")
    sel_tiendas = st.sidebar.multiselect("Unidades de Negocio:", sorted(df_raw['Tienda'].unique().tolist()), default=df_raw['Tienda'].unique().tolist())
    sel_meses = st.sidebar.multiselect("Periodo Mensual:", ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'], default=df_raw['Mes'].unique().tolist())
    
    df_f = df_raw[(df_raw['Tienda'].isin(sel_tiendas)) & (df_raw['Mes'].isin(sel_meses))]

    st.markdown('<p class="main-title">PRICE SHOES • Executive Command Center</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">BI & OPERATIONAL PROFITABILITY SCORECARD</p>', unsafe_allow_html=True)

    # --- PESTAÑAS ESTRATÉGICAS ---
    t_score, t_conv, t_prod, t_rent = st.tabs(["📊 SCORECARD EJECUTIVO", "🔄 CONVERSIÓN A VENTA", "👥 PRODUCTIVIDAD", "💰 RENTABILIDAD"])

    # --- KPI CALCULATIONS ---
    ing = df_f['Total_Ing'].sum()
    hab = df_f['Pzas_Hab'].sum()
    ubi = df_f['Pzas_Ubi'].sum()
    vta = df_f['Venta_Est'].sum()
    rec_m, rec_r = df_f['Meta_Rec'].sum(), df_f['Real_Rec'].sum()
    val_rec = df_f['Valor_Rec_Est'].sum()
    cost_rec = df_f['Costo_Rec_Est'].sum()

    with t_score:
        # Fila 1: Operación
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: st.markdown(f'<div class="kpi-card"><p class="kpi-label">📥 Ingresos</p><p class="kpi-value">{ing:,.0f}</p></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="kpi-card"><p class="kpi-label">✨ Habilitado</p><p class="kpi-value">{(hab/ing*100 if ing>0 else 0):.1f}%</p></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="kpi-card"><p class="kpi-label">📍 Ubicado</p><p class="kpi-value">{(ubi/ing*100 if ing>0 else 0):.1f}%</p></div>', unsafe_allow_html=True)
        with c4: st.markdown(f'<div class="kpi-card"><p class="kpi-label">🎯 Efic. Recorridos</p><p class="kpi-value">{(rec_r/rec_m*100 if rec_m>0 else 0):.1f}%</p></div>', unsafe_allow_html=True)
        with c5: st.markdown(f'<div class="kpi-card"><p class="kpi-label">🛒 Conv. Venta</p><p class="kpi-value">{(vta/ing*100 if ing>0 else 0):.1f}%</p></div>', unsafe_allow_html=True)

        # Alertas y Funnel
        col_f, col_a = st.columns([2, 1])
        with col_f:
            fig_fun = go.Figure(go.Funnel(
                y = ["Ingreso", "Habilitado", "Ubicado", "Venta Est."],
                x = [ing, hab, ubi, vta],
                marker = {"color": ["#1F497D", "#E6007E", "#555555", "#A6A6A6"]}
            ))
            fig_fun.update_layout(title="Funnel Operativo: Recuperación a Venta", height=400)
            st.plotly_chart(fig_fun, use_container_width=True, config={'staticPlot': True})
        with col_a:
            st.markdown("### ⚠️ Alertas de Gestión")
            if (hab/ing if ing>0 else 1) < 0.8: st.markdown('<div class="exec-alert alert-critical">Habilitado Crítico: Bajo el 80%</div>', unsafe_allow_html=True)
            if (rec_r/rec_m if rec_m>0 else 1) < 0.9: st.markdown('<div class="exec-alert alert-warning">Recorridos Insuficientes detectados</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="exec-alert alert-warning">Mejor Tienda: {df_f.groupby("Tienda")["Total_Ing"].sum().idxmax()}</div>', unsafe_allow_html=True)

    with t_conv:
        st.markdown("### 🔄 Análisis de Conversión Semanal")
        df_conv = df_f.groupby('Semana').agg({'Total_Ing':'sum', 'Venta_Est':'sum'}).reset_index()
        df_conv['% Conv'] = (df_conv['Venta_Est'] / df_conv['Total_Ing'] * 100).fillna(0)
        fig_c = px.line(df_conv, x='Semana', y='% Conv', title="Tendencia de Conversión a Venta WoW", markers=True, color_discrete_sequence=['#E6007E'])
        st.plotly_chart(fig_c, use_container_width=True, config={'staticPlot': True})
        
        # Ranking de Conversión por Tienda
        df_t_c = df_f.groupby('Tienda').agg({'Total_Ing':'sum', 'Venta_Est':'sum'}).reset_index()
        df_t_c['% Conv'] = (df_t_c['Venta_Est'] / df_t_c['Total_Ing'] * 100).fillna(0)
        st.plotly_chart(px.bar(df_t_c.sort_values('% Conv', ascending=False), x='Tienda', y='% Conv', title="Ranking de Conversión por Tienda", color_discrete_sequence=['#1F497D']), use_container_width=True)

    with t_prod:
        st.markdown("### 👥 Productividad por Tienda y Semana")
        df_p = df_f.groupby(['Semana', 'Tienda']).agg({'Total_Ing':'sum', 'Pzas_Hab':'sum', 'Pzas_Ubi':'sum'}).reset_index()
        st.dataframe(df_p, use_container_width=True)
        st.plotly_chart(px.scatter(df_p, x='Total_Ing', y='Pzas_Hab', size='Pzas_Ubi', color='Tienda', title="Matriz de Productividad: Ingreso vs Habilitado"), use_container_width=True)

    with t_rent:
        st.markdown("### 💰 Análisis de Rentabilidad Operativa")
        cr1, cr2 = st.columns(2)
        with cr1:
            st.markdown(f'<div class="kpi-card"><p class="kpi-label">Valor Recuperado ($)</p><p class="kpi-value">${val_rec:,.0f}</p></div>', unsafe_allow_html=True)
        with cr2:
            st.markdown(f'<div class="kpi-card"><p class="kpi-label">Costo de Recuperación ($)</p><p class="kpi-value">${cost_rec:,.0f}</p></div>', unsafe_allow_html=True)
        
        # Pareto de Tiendas por Costo
        df_cost = df_f.groupby('Tienda')['Costo_Rec_Est'].sum().reset_index().sort_values('Costo_Rec_Est', ascending=False)
        st.plotly_chart(px.bar(df_cost, x='Tienda', y='Costo_Rec_Est', title="Distribución de Costo de Recuperación por Tienda", color_discrete_sequence=['#1F497D']), use_container_width=True)

else:
    st.info("📊 Inicializando Scorecard Ejecutivo... Verifica la conexión con el Google Sheet.")
