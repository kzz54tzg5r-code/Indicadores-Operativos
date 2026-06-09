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

st.markdown("""
    <style>
    .main { background-color: #F8F9FB; }
    .main-title { color: #1F497D; font-size: 36px; font-weight: 900; letter-spacing: -1.5px; margin-bottom: 0px; }
    .sub-title { color: #E6007E; font-size: 14px; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 25px; }
    
    /* WoW Cards */
    .wow-card-header { background-color: #1F497D; color: white; text-align: center; padding: 6px; border-radius: 6px 6px 0 0; font-weight: bold; font-size: 12px; }
    .wow-card-body { background-color: white; border: 1px solid #E0E0E0; border-top: none; border-radius: 0 0 6px 6px; padding: 10px; margin-bottom: 15px; }
    .wow-metric-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; border-bottom: 1px solid #EEE; padding-bottom: 2px; }
    .wow-label { color: #666; font-size: 9px; font-weight: 700; text-transform: uppercase; }
    .wow-value { color: #1F497D; font-size: 14px; font-weight: 800; }
    
    /* KPI Master Cards */
    .kpi-master { background-color: white; border-radius: 12px; padding: 18px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border-top: 5px solid #1F497D; text-align: center; }
    .kpi-master-label { color: #666; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }
    .kpi-master-value { color: #1F497D; font-size: 28px; font-weight: 900; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_all_intelligence_data():
    URL_XLSX = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSV6dtosg0Ydt0o3NMFezC--NjHfEW82onFeY2JR4PTYD3ylG4ZlRaQBquscFrCy_Lysrau9zTW6dkn/pub?output=xlsx"
    URL_CSV = "https://drive.google.com/uc?export=download&id=15UBabZ8g_VbDMZiPfR2iuW-U9YuNgHWP"
    
    try:
        resp_x = requests.get(URL_XLSX, timeout=30)
        xls = pd.ExcelFile(BytesIO(resp_x.content), engine='openpyxl')
        
        all_op = []
        df_models = pd.DataFrame()
        model_cols = {}
        
        for sheet in xls.sheet_names:
            if 'sem' in sheet.lower():
                raw = pd.read_excel(xls, sheet_name=sheet, header=None, engine='openpyxl')
                h_rows = raw[raw[1] == 'Tienda'].index.tolist()
                for h_idx in h_rows:
                    fecha = raw.iloc[h_idx-1, 1]
                    if not isinstance(fecha, datetime): continue
                    d_idx = h_idx + 1
                    while d_idx < len(raw) and pd.notna(raw.iloc[d_idx, 1]):
                        r = raw.iloc[d_idx, 1:15].tolist()
                        all_op.append({'Tienda': r[0], 'Total_Ing': r[5], 'Meta_Rec': r[6], 'Real_Rec': r[7], 'Pzas_Hab': r[9], 'Pzas_Ubi': r[10], 'Fecha': fecha, 'Semana': sheet})
                        d_idx += 1
            if 'venta' in sheet.lower() or 'devolucion' in sheet.lower():
                df_models = pd.read_excel(xls, sheet_name=sheet, engine='openpyxl')
                df_models.columns = [str(c).strip() for c in df_models.columns]
                cmap = {'id':['id','ID'], 'modelo':['modelo','Modelo'], 'color':['color','Color'], 'merca':['merca','Merca','Marca'], 'devolucion':['devolucion','Devolucion'], 'venta':['venta','Venta'], 'tienda':['tienda','Tienda','Ubicación']}
                for k, v in cmap.items():
                    for key in v:
                        for c in df_models.columns:
                            if key.lower() in c.lower(): model_cols[k] = c

        df_op = pd.DataFrame(all_op)
        for c in ['Total_Ing', 'Real_Rec', 'Pzas_Hab', 'Pzas_Ubi', 'Meta_Rec']:
            df_op[c] = pd.to_numeric(df_op[c], errors='coerce').fillna(0)
        
        meses_dict = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
        df_op['Mes'] = df_op['Fecha'].dt.month.map(meses_dict)
        
        resp_c = requests.get(URL_CSV, timeout=30)
        df_m = pd.read_csv(BytesIO(resp_c.content), encoding='latin1', low_memory=False)
        df_m.columns = [c.strip() for c in df_m.columns]
        df_m = df_m.rename(columns={'Ubicación': 'Tienda', 'Número de Piezas': 'Pzas', 'Actividad Realizada': 'Actividad'})
        
        return df_op, df_models, model_cols, df_m
    except Exception as e:
        st.error(f"Error BI: {e}")
        return pd.DataFrame(), pd.DataFrame(), {}, pd.DataFrame()

df_op, df_models, m_cols, df_m = load_all_intelligence_data()

if not df_op.empty:
    st.sidebar.image("https://priceshoes.com/media/logo/stores/1/logo_price_shoes.png", width=160)
    
    # --- FILTROS EN SIDEBAR ---
    st.sidebar.markdown("### 🎛️ Filtros")
    sel_tiendas = st.sidebar.multiselect("Tiendas:", sorted(df_op['Tienda'].unique().tolist()), default=df_op['Tienda'].unique().tolist())
    sel_meses = st.sidebar.multiselect("Meses:", ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'], default=df_op['Mes'].unique().tolist())
    
    actividades_list = sorted(df_m['Actividad'].unique().tolist()) if not df_m.empty else []
    sel_actividades = st.sidebar.multiselect("Actividades:", actividades_list, default=actividades_list)
    
    df_f = df_op[(df_op['Tienda'].isin(sel_tiendas)) & (df_op['Mes'].isin(sel_meses))]

    st.markdown('<p class="main-title">PRICE SHOES • Executive Command Center</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">BI & OPERATIONAL SCORECARD</p>', unsafe_allow_html=True)

    # --- 1. COMPARATIVOS WoW ÚLTIMAS 4 SEMANAS ---
    st.markdown("### 📊 Comparativo Semanal (Últimas 4 Semanas)")
    all_weeks = sorted(df_op['Semana'].unique().tolist(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    w_show = all_weeks[-4:]
    cols_w = st.columns(4)
    for i, sem in enumerate(w_show):
        df_c = df_op[df_op['Semana'] == sem]
        if sel_tiendas: df_c = df_c[df_c['Tienda'].isin(sel_tiendas)]
        ing, hab, ubi = df_c['Total_Ing'].sum(), df_c['Pzas_Hab'].sum(), df_c['Pzas_Ubi'].sum()
        with cols_w[i]:
            st.markdown(f'<div class="wow-card-header">{sem}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="wow-card-body"><div class="wow-metric-row"><span class="wow-label">Ingreso</span><span class="wow-value">{ing:,.0f}</span></div><div class="wow-metric-row"><span class="wow-label">Hab.</span><span class="wow-value">{hab:,.0f}</span></div><div class="wow-metric-row"><span class="wow-label">Ubi.</span><span class="wow-value">{ubi:,.0f}</span></div></div>', unsafe_allow_html=True)

    # --- TABS ---
    t_exec, t_prod, t_model, t_audit = st.tabs(["📊 SCORECARD EJECUTIVO", "👥 RANKING COLABORADORES", "👟 TOP 30 MODELOS", "📑 AUDITORÍA"])

    with t_exec:
        ing_t, hab_t, ubi_t = df_f['Total_Ing'].sum(), df_f['Pzas_Hab'].sum(), df_f['Pzas_Ubi'].sum()
        rec_m, rec_r = df_f['Meta_Rec'].sum(), df_f['Real_Rec'].sum()
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f'<div class="kpi-master"><p class="kpi-master-label">📥 Ingresos</p><p class="kpi-master-value">{ing_t:,.0f}</p></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="kpi-master"><p class="kpi-master-label">✨ Habilitado</p><p class="kpi-master-value">{(hab_t/ing_t*100 if ing_t>0 else 0):.1f}%</p></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="kpi-master"><p class="kpi-master-label">📍 Ubicado</p><p class="kpi-master-value">{(ubi_t/ing_t*100 if ing_t>0 else 0):.1f}%</p></div>', unsafe_allow_html=True)
        with c4: st.markdown(f'<div class="kpi-master"><p class="kpi-master-label">🎯 Recorridos</p><p class="kpi-master-value">{(rec_r/rec_m*100 if rec_m>0 else 0):.1f}%</p></div>', unsafe_allow_html=True)
        
        fig_f = px.funnel(x=[ing_t, hab_t, ubi_t], y=["Ingreso", "Habilitado", "Ubicado"], color_discrete_sequence=['#1F497D'])
        st.plotly_chart(fig_f, use_container_width=True, config={'staticPlot': True})

    with t_prod:
        st.markdown("### 🏆 Ranking de Productividad por Colaborador")
        if not df_m.empty:
            df_m_f = df_m[(df_m['Tienda'].isin(sel_tiendas)) & (df_m['Actividad'].isin(sel_actividades))]
            df_user = df_m_f.groupby(['Nombre', 'Tienda']).agg({'Pzas': 'sum'}).reset_index().sort_values('Pzas', ascending=False)
            st.plotly_chart(px.bar(df_user.head(20), x='Nombre', y='Pzas', color='Tienda', title="Top 20 Colaboradores por Volumen"), use_container_width=True)
            st.dataframe(df_user, use_container_width=True)

    with t_model:
        st.markdown("### 🏆 Top 30 Modelos por Tienda")
        if not df_models.empty and 'tienda' in m_cols:
            t_sel = st.selectbox("Seleccionar Tienda para Ranking:", ["Todas"] + sel_tiendas)
            df_mf = df_models.copy()
            if t_sel != "Todas": df_mf = df_mf[df_mf[m_cols['tienda']] == t_sel]
            d, v = m_cols['devolucion'], m_cols['venta']
            df_mf['Conv_%'] = (pd.to_numeric(df_mf[v], errors='coerce') / pd.to_numeric(df_mf[d], errors='coerce') * 100).fillna(0)
            st.dataframe(df_mf.sort_values('Conv_%', ascending=False).head(30), use_container_width=True)

    with t_audit:
        st.dataframe(df_f, use_container_width=True)

else: st.info("📊 Conectando con la base de datos...")
