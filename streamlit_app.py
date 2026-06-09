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
    .main-title { color: #1F497D; font-size: 38px; font-weight: 900; letter-spacing: -1.5px; margin-bottom: 0px; }
    .sub-title { color: #E6007E; font-size: 14px; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 25px; }
    
    /* WoW Cards */
    .wow-card-header { background-color: #1F497D; color: white; text-align: center; padding: 6px; border-radius: 6px 6px 0 0; font-weight: bold; font-size: 13px; }
    .wow-card-body { background-color: white; border: 1px solid #E0E0E0; border-top: none; border-radius: 0 0 6px 6px; padding: 12px; margin-bottom: 15px; }
    .wow-metric-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; border-bottom: 1px solid #EEE; padding-bottom: 4px; }
    .wow-label { color: #666; font-size: 10px; font-weight: 700; text-transform: uppercase; }
    .wow-value { color: #1F497D; font-size: 15px; font-weight: 800; }
    .wow-trend { font-size: 12px; font-weight: 800; }
    .trend-up { color: #28A745; }
    .trend-down { color: #DC3545; }
    
    /* Store Section */
    .store-header { background-color: #1F497D; color: white; padding: 8px; border-radius: 8px; font-weight: 900; font-size: 16px; margin-top: 20px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_master_data():
    URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSV6dtosg0Ydt0o3NMFezC--NjHfEW82onFeY2JR4PTYD3ylG4ZlRaQBquscFrCy_Lysrau9zTW6dkn/pub?output=xlsx"
    try:
        response = requests.get(URL, timeout=30)
        xls = pd.ExcelFile(BytesIO(response.content), engine='openpyxl')
        
        # 1. Datos Operativos
        all_op = []
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
                        all_op.append({
                            'Tienda': r[0], 'Ing_Aduana_Sis': r[1], 'Ing_Aduana': r[2], 
                            'Ing_Muertos': r[3], 'Ing_Cajas': r[4], 'Total_Ing': r[5],
                            'Real_Rec': r[7], 'Pzas_Hab': r[9], 'Pzas_Ubi': r[10],
                            'Fecha': fecha, 'Semana': sheet
                        })
                        d_idx += 1
        
        # 2. Datos de Modelos
        df_models = pd.DataFrame()
        final_cols = {}
        for sheet in xls.sheet_names:
            if 'venta' in sheet.lower() or 'devolucion' in sheet.lower():
                df_models = pd.read_excel(xls, sheet_name=sheet, engine='openpyxl')
                df_models.columns = [str(c).strip() for c in df_models.columns]
                col_map = {
                    'id': ['id', 'ID'], 'modelo': ['modelo', 'Modelo'],
                    'color': ['color', 'Color'], 'merca': ['merca', 'Merca', 'Marca'],
                    'devolucion': ['devolucion', 'Devolucion'], 'venta': ['venta', 'Venta'],
                    'tienda': ['tienda', 'Tienda', 'Ubicación']
                }
                for k, v in col_map.items():
                    for key in v:
                        for c in df_models.columns:
                            if key.lower() in c.lower(): final_cols[k] = c
                break

        df_op = pd.DataFrame(all_op)
        for c in ['Total_Ing', 'Real_Rec', 'Pzas_Hab', 'Pzas_Ubi']:
            df_op[c] = pd.to_numeric(df_op[c], errors='coerce').fillna(0)
        
        meses = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
        df_op['Mes'] = df_op['Fecha'].dt.month.map(meses)
        
        return df_op, df_models, final_cols
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), {}

df_op, df_models, model_cols = load_master_data()

if not df_op.empty:
    st.sidebar.image("https://priceshoes.com/media/logo/stores/1/logo_price_shoes.png", width=160)
    sel_tiendas = st.sidebar.multiselect("Tiendas:", sorted(df_op['Tienda'].unique().tolist()), default=df_op['Tienda'].unique().tolist())
    sel_meses = st.sidebar.multiselect("Meses:", ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'], default=df_op['Mes'].unique().tolist())
    
    df_f = df_op[(df_op['Tienda'].isin(sel_tiendas)) & (df_op['Mes'].isin(sel_meses))]

    st.markdown('<p class="main-title">PRICE SHOES • Operational Intelligence Center</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">CENTRO DE MANDO EJECUTIVO, PRODUCTIVIDAD Y PRODUCTO</p>', unsafe_allow_html=True)

    # --- 1. COMPARATIVOS ÚLTIMAS 4 SEMANAS (INICIO) ---
    st.markdown("### 📊 Comparativo Semanal (WoW)")
    all_weeks = sorted(df_op['Semana'].unique().tolist(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    weeks_show = all_weeks[-4:]
    cols_w = st.columns(4)
    for i, sem in enumerate(weeks_show):
        df_curr = df_op[df_op['Semana'] == sem]
        if sel_tiendas: df_curr = df_curr[df_curr['Tienda'].isin(sel_tiendas)]
        
        ing, hab, ubi = df_curr['Total_Ing'].sum(), df_curr['Pzas_Hab'].sum(), df_curr['Pzas_Ubi'].sum()
        
        with cols_w[i]:
            st.markdown(f'<div class="wow-card-header">{sem}</div>', unsafe_allow_html=True)
            st.markdown(f"""
                <div class="wow-card-body">
                    <div class="wow-metric-row"><span class="wow-label">Ingreso</span><span class="wow-value">{ing:,.0f}</span></div>
                    <div class="wow-metric-row"><span class="wow-label">Habilitado</span><span class="wow-value">{hab:,.0f}</span></div>
                    <div class="wow-metric-row"><span class="wow-label">Ubicado</span><span class="wow-value">{ubi:,.0f}</span></div>
                </div>
            """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📍 DESEMPEÑO TIENDAS", "👟 TOP 30 MODELOS", "👥 PRODUCTIVIDAD"])

    with tab1:
        for tienda in sorted(sel_tiendas):
            st.markdown(f'<div class="store-header">📍 {tienda.upper()}</div>', unsafe_allow_html=True)
            df_t = df_f[df_f['Tienda'] == tienda]
            ing, hab, ubi = df_t['Total_Ing'].sum(), df_t['Pzas_Hab'].sum(), df_t['Pzas_Ubi'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Ingresos", f"{ing:,.0f}")
            c2.metric("Habilitado", f"{hab:,.0f}", f"{(hab/ing*100 if ing>0 else 0):.1f}%")
            c3.metric("Ubicado", f"{ubi:,.0f}", f"{(ubi/ing*100 if ing>0 else 0):.1f}%")

    with tab2:
        st.markdown("### 🏆 Top 30 Modelos por Tienda")
        if not df_models.empty and 'tienda' in model_cols:
            t_sel = st.selectbox("Filtrar Modelos por Tienda:", ["Todas"] + sel_tiendas)
            df_m_f = df_models.copy()
            if t_sel != "Todas": df_m_f = df_m_f[df_m_f[model_cols['tienda']] == t_sel]
            
            d, v = model_cols['devolucion'], model_cols['venta']
            df_m_f['Conv_%'] = (pd.to_numeric(df_m_f[v], errors='coerce') / pd.to_numeric(df_m_f[d], errors='coerce') * 100).fillna(0)
            st.dataframe(df_m_f.sort_values('Conv_%', ascending=False).head(30), use_container_width=True)

    with tab3:
        st.markdown("### 👥 Ranking de Colaboradores")
        # Nota: Asumiendo que hay una columna 'Nombre' o similar en la base maestra
        st.info("Agregando métricas de productividad por usuario basadas en el volumen procesado.")
        df_u = df_f.groupby('Tienda').agg({'Pzas_Hab':'sum', 'Pzas_Ubi':'sum'}).reset_index()
        st.plotly_chart(px.bar(df_u, x='Tienda', y=['Pzas_Hab', 'Pzas_Ubi'], barmode='group', title="Eficiencia Operativa por Unidad"), use_container_width=True)

else:
    st.info("📊 Conectando con la base de datos... Verifica el Google Sheet.")
