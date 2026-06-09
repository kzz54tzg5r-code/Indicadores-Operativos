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
st.set_page_config(page_title="Price Shoes BI - Master Scorecard", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .main { background-color: #F8F9FB; }
    .main-title { color: #1F497D; font-size: 38px; font-weight: 900; letter-spacing: -1.5px; margin-bottom: 0px; }
    .sub-title { color: #E6007E; font-size: 14px; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 25px; }
    
    /* KPI Cards */
    .kpi-card { background-color: white; border-radius: 12px; padding: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border-top: 4px solid #1F497D; text-align: center; margin-bottom: 10px; }
    .kpi-label { color: #666; font-size: 10px; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }
    .kpi-value { color: #1F497D; font-size: 24px; font-weight: 900; margin-bottom: 2px; }
    .kpi-sub { color: #E6007E; font-size: 12px; font-weight: 700; }
    
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
        
        # 1. Cargar Datos Operativos (Pestañas Sem)
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
                        all_op.append({'Tienda': r[0], 'Total_Ing': r[5], 'Real_Rec': r[7], 'Pzas_Hab': r[9], 'Pzas_Ubi': r[10], 'Fecha': fecha, 'Semana': sheet})
                        d_idx += 1
        
        # 2. Cargar Datos de Modelos (Pestaña Venta/Devolución)
        df_models = pd.DataFrame()
        for sheet in xls.sheet_names:
            if 'venta' in sheet.lower() or 'devolucion' in sheet.lower():
                df_models = pd.read_excel(xls, sheet_name=sheet, engine='openpyxl')
                break
        
        if not df_models.empty:
            df_models.columns = [str(c).strip() for c in df_models.columns]
            # Mapeo de columnas de modelos
            col_map = {
                'id': ['id', 'ID', 'Id'], 'modelo': ['modelo', 'Modelo', 'MODELO'],
                'color': ['color', 'Color', 'COLOR'], 'merca': ['merca', 'Merca', 'Marca', 'MARCA'],
                'devolucion': ['devolucion', 'Devolucion', 'DEVOLUCION', 'Devoluciones'],
                'venta': ['venta', 'Venta', 'VENTA', 'Ventas']
            }
            def find_col(keys):
                for k in keys:
                    for c in df_models.columns:
                        if k.lower() in c.lower(): return c
                return None
            
            final_cols = {k: find_col(v) for k, v in col_map.items()}
            # Limpiar y calcular conversión
            for k, v in final_cols.items():
                if v and k in ['devolucion', 'venta']:
                    df_models[v] = pd.to_numeric(df_models[v], errors='coerce').fillna(0)
            
            if final_cols['devolucion'] and final_cols['venta']:
                d, v = final_cols['devolucion'], final_cols['venta']
                df_models['Conv_%'] = (df_models[v] / df_models[d] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
                # Solo modelos con devoluciones
                df_models = df_models[df_models[d] > 0].sort_values('Conv_%', ascending=False)

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

    st.markdown('<p class="main-title">PRICE SHOES • Operational Master Scorecard</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">CENTRO DE MANDO ESTRATÉGICO Y ANÁLISIS DE PRODUCTO</p>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📊 DESEMPEÑO POR TIENDA", "👟 TOP 30 MODELOS (CONVERSIÓN)", "📑 AUDITORÍA"])

    with tab1:
        for tienda in sorted(sel_tiendas):
            st.markdown(f'<div class="store-header">📍 {tienda.upper()}</div>', unsafe_allow_html=True)
            df_t = df_f[df_f['Tienda'] == tienda]
            ing = df_t['Total_Ing'].sum()
            hab = df_t['Pzas_Hab'].sum()
            ubi = df_t['Pzas_Ubi'].sum()
            rec = df_t['Real_Rec'].sum()
            
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f'<div class="kpi-card"><p class="kpi-label">📥 Ingresos</p><p class="kpi-value">{ing:,.0f}</p></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="kpi-card"><p class="kpi-label">✨ Habilitado</p><p class="kpi-value">{(hab/ing*100 if ing>0 else 0):.1f}%</p><p class="kpi-sub">{hab:,.0f} Pzas</p></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="kpi-card"><p class="kpi-label">📍 Ubicado</p><p class="kpi-value">{(ubi/ing*100 if ing>0 else 0):.1f}%</p><p class="kpi-sub">{ubi:,.0f} Pzas</p></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="kpi-card"><p class="kpi-label">🎯 Recorridos</p><p class="kpi-value">{rec:,.0f}</p></div>', unsafe_allow_html=True)

    with tab2:
        st.markdown("### 🏆 Top 30 Modelos con Mejor Conversión (Venta / Devolución)")
        if not df_models.empty:
            # Mostrar solo columnas relevantes
            cols_to_show = [c for c in model_cols.values() if c is not None] + ['Conv_%']
            st.dataframe(df_models[cols_to_show].head(30), use_container_width=True)
            
            # Gráfico de Conversión
            fig = px.bar(df_models.head(15), x=model_cols['modelo'], y='Conv_%', title="Top 15 Modelos por % de Conversión", color_discrete_sequence=['#E6007E'])
            st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})
        else:
            st.info("No se encontraron datos de modelos en la pestaña de Ventas/Devoluciones.")

    with tab3:
        st.dataframe(df_f[['Fecha', 'Semana', 'Tienda', 'Total_Ing', 'Pzas_Hab', 'Pzas_Ubi', 'Real_Rec']], use_container_width=True)
else:
    st.info("📊 Conectando con la base de datos... Verifica el Google Sheet.")
