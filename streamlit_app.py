import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO
from datetime import datetime
import gc

# =========================================================================
# --- CONFIGURACIÓN DE NIVEL BI DIRECTOR (v13) ---
# =========================================================================
st.set_page_config(page_title="Price Shoes BI - Ultimate Master Center", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .main { background-color: #F8F9FB; }
    .main-title { color: #1F497D; font-size: 36px; font-weight: 900; letter-spacing: -1.5px; margin-bottom: 0px; }
    .sub-title { color: #E6007E; font-size: 14px; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 25px; }
    .wow-card-header { background-color: #1F497D; color: white; text-align: center; padding: 6px; border-radius: 6px 6px 0 0; font-weight: bold; font-size: 12px; }
    .wow-card-body { background-color: white; border: 1px solid #E0E0E0; border-top: none; border-radius: 0 0 6px 6px; padding: 10px; margin-bottom: 15px; }
    .wow-metric-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; border-bottom: 1px solid #EEE; padding-bottom: 2px; }
    .wow-label { color: #666; font-size: 9px; font-weight: 700; text-transform: uppercase; }
    .wow-value { color: #1F497D; font-size: 14px; font-weight: 800; }
    .wow-value-pct { color: #E6007E; font-size: 13px; font-weight: 900; }
    .kpi-master { background-color: white; border-radius: 12px; padding: 18px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border-top: 5px solid #1F497D; text-align: center; }
    .kpi-master-label { color: #666; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }
    .kpi-master-value { color: #1F497D; font-size: 28px; font-weight: 900; }
    .store-row { background-color: #f1f3f6; padding: 8px; border-radius: 8px; margin-top: 20px; margin-bottom: 10px; font-weight: bold; color: #1F497D; border-left: 5px solid #1F497D; }
    </style>
    """, unsafe_allow_html=True)

def to_num(val):
    try:
        if pd.isna(val): return 0
        return float(str(val).replace('$', '').replace(',', '').replace(' ', ''))
    except: return 0

def safe_div(num, den):
    return (num / den) if den and den > 0 else 0

@st.cache_data(ttl=600)
def load_all_intelligence_data():
    URL_XLSX = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSd7J_FSk0829VZzHVRn4DoJx-E2CT4iK_nKq026i6B8UaPLeoyX5eRtCXYIaZO2pWGPS4Wd94inFYw/pub?output=xlsx"
    URL_CSV = "https://drive.google.com/uc?export=download&id=15UBabZ8g_VbDMZiPfR2iuW-U9YuNgHWP"
    
    try:
        resp = requests.get(URL_XLSX, timeout=180)
        xls = pd.ExcelFile(BytesIO(resp.content), engine='openpyxl')
        
        df_op = pd.DataFrame()
        df_models = pd.DataFrame()
        
        # 1. Datos Operativos (Pestaña 'Base de datos muertos y cambios')
        base_sheet = [s for s in xls.sheet_names if 'base de datos' in s.lower()]
        if base_sheet:
            df_b = pd.read_excel(xls, sheet_name=base_sheet[0], engine='openpyxl')
            df_b.columns = [str(c).strip() for c in df_b.columns]
            df_op = df_b.rename(columns={
                'Ubicación': 'Tienda', 'Piezas de Ingreso': 'Total_Ing', 
                'Piezas Habilitadas': 'Pzas_Hab', 'Piezas Ubicadas': 'Pzas_Ubi',
                'Recorridos Realizados': 'Real_Rec', 'Meta de Recorridos': 'Meta_Rec'
            })
            # Asegurar que existan las columnas
            for c in ['Total_Ing', 'Pzas_Hab', 'Pzas_Ubi', 'Real_Rec', 'Meta_Rec']:
                if c not in df_op.columns: df_op[c] = 0
                else: df_op[c] = df_op[c].apply(to_num)
            
            if 'Fecha' in df_op.columns:
                df_op['Fecha'] = pd.to_datetime(df_op['Fecha'], errors='coerce')
                df_op['Semana'] = df_op['Fecha'].dt.isocalendar().week.apply(lambda x: f"Sem {x}")
            else:
                df_op['Semana'] = "Sem Actual"

        # 2. Datos de Modelos (Pestaña 'Venta y devolucion')
        model_sheet = [s for s in xls.sheet_names if 'venta y devolucion' in s.lower()]
        if model_sheet:
            df_m_raw = pd.read_excel(xls, sheet_name=model_sheet[0], header=None, engine='openpyxl', nrows=2000)
            fechas = df_m_raw.iloc[0].tolist()
            cabeceras = df_m_raw.iloc[1].tolist()
            
            idx_mod = cabeceras.index('Modelo') if 'Modelo' in cabeceras else 4
            idx_col = cabeceras.index('Color') if 'Color' in cabeceras else 7
            idx_mar = cabeceras.index('Marca Price') if 'Marca Price' in cabeceras else 3
            idx_tie = cabeceras.index('Tiendas') if 'Tiendas' in cabeceras else 25
            
            melted = []
            for i in range(25, len(cabeceras), 3):
                if i+2 >= len(cabeceras) or pd.isna(fechas[i]): continue
                try:
                    f_dt = pd.to_datetime(fechas[i])
                    sem_label = f"Sem {f_dt.isocalendar().week}"
                    subset = df_m_raw.iloc[2:, [idx_mod, idx_col, idx_mar, idx_tie, i, i+1, i+2]].copy()
                    subset.columns = ['Modelo', 'Color', 'Marca', 'Tienda', 'Venta', 'Dev', 'Neta_$']
                    subset['Semana'] = sem_label
                    melted.append(subset)
                except: continue
            if melted:
                df_models = pd.concat(melted, ignore_index=True)
                for c in ['Venta', 'Dev', 'Neta_$']: 
                    df_models[c] = df_models[c].apply(to_num)

        # 3. Colaboradores (CSV)
        resp_c = requests.get(URL_CSV, timeout=60)
        df_colab = pd.read_csv(BytesIO(resp_c.content), encoding='latin1', low_memory=False)
        df_colab = df_colab.rename(columns={'Ubicación': 'Tienda', 'Numero de Piezas': 'Pzas', 'Número de Piezas': 'Pzas'})
        
        return df_op, df_models, df_colab
    except Exception as e:
        st.error(f"Error de carga: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_op, df_models, df_colab = load_all_intelligence_data()

if not df_op.empty:
    st.sidebar.image("https://priceshoes.com/media/logo/stores/1/logo_price_shoes.png", width=160)
    st.sidebar.markdown("### Filtros Globales")
    
    weeks = sorted(df_op['Semana'].unique())
    sel_w = st.sidebar.multiselect("Semanas:", weeks, default=weeks[-2:] if len(weeks)>1 else weeks)
    stores = sorted(df_op['Tienda'].unique())
    sel_s = st.sidebar.multiselect("Tiendas:", stores, default=stores)
    
    df_f = df_op[(df_op['Semana'].isin(sel_w)) & (df_op['Tienda'].isin(sel_s))]

    st.markdown('<p class="main-title">PRICE SHOES • Operational Intelligence Center</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">CENTRO DE MANDO EJECUTIVO, PRODUCTIVIDAD Y PRODUCTO</p>', unsafe_allow_html=True)

    # --- COMPARATIVO WoW ---
    st.markdown("### Comparativo Semanal (WoW)")
    w_show = weeks[-4:]
    cols_w = st.columns(len(w_show))
    for i, sem in enumerate(w_show):
        df_c = df_op[df_op['Semana'] == sem]
        if sel_s: df_c = df_c[df_c['Tienda'].isin(sel_s)]
        ing, hab, ubi, rm, rr = df_c['Total_Ing'].sum(), df_c['Pzas_Hab'].sum(), df_c['Pzas_Ubi'].sum(), df_c['Meta_Rec'].sum(), df_c['Real_Rec'].sum()
        with cols_w[i]:
            st.markdown(f'<div class="wow-card-header">{sem}</div>', unsafe_allow_html=True)
            st.markdown(f'''<div class="wow-card-body">
                <div class="wow-metric-row"><span class="wow-label">Ingreso</span><span class="wow-value">{ing:,.0f}</span></div>
                <div class="wow-metric-row"><span class="wow-label">% Hab/Ing</span><span class="wow-value-pct">{safe_div(hab,ing)*100:.1f}%</span></div>
                <div class="wow-metric-row"><span class="wow-label">% Ubi/Ing</span><span class="wow-value-pct">{safe_div(ubi,ing)*100:.1f}%</span></div>
                <div class="wow-metric-row"><span class="wow-label">% Rec vs Meta</span><span class="wow-value-pct">{safe_div(rr,rm)*100:.1f}%</span></div>
            </div>''', unsafe_allow_html=True)

    # --- TABS ---
    t_exec, t_prod, t_model, t_conv, t_audit = st.tabs(["SCORECARD", "COLABORADORES", "TOP 30 MODELOS", "CONVERSIÓN", "AUDITORÍA"])

    with t_exec:
        st.markdown("### Consolidado Global")
        i_t, h_t, u_t, rm_t, rr_t = df_f['Total_Ing'].sum(), df_f['Pzas_Hab'].sum(), df_f['Pzas_Ubi'].sum(), df_f['Meta_Rec'].sum(), df_f['Real_Rec'].sum()
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f'<div class="kpi-master"><p class="kpi-master-label">Ingresos</p><p class="kpi-master-value">{i_t:,.0f}</p></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="kpi-master"><p class="kpi-master-label">Habilitado / Ingreso</p><p class="kpi-master-value">{safe_div(h_t, i_t) * 100:.1f}%</p></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="kpi-master"><p class="kpi-master-label">Ubicado / Ingreso</p><p class="kpi-master-value">{safe_div(u_t, i_t) * 100:.1f}%</p></div>', unsafe_allow_html=True)
        with c4: st.markdown(f'<div class="kpi-master"><p class="kpi-master-label">Recorridos vs Meta</p><p class="kpi-master-value">{safe_div(rr_t, rm_t) * 100:.1f}%</p></div>', unsafe_allow_html=True)
        
        st.markdown("### Desglose por Tienda")
        for t in sorted(df_f['Tienda'].unique()):
            dt = df_f[df_f['Tienda'] == t]
            it, ht, ut, rmt, rrt = dt['Total_Ing'].sum(), dt['Pzas_Hab'].sum(), dt['Pzas_Ubi'].sum(), dt['Meta_Rec'].sum(), dt['Real_Rec'].sum()
            st.markdown(f'<div class="store-row">📍 {t}</div>', unsafe_allow_html=True)
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Ingresos", f"{it:,.0f}")
            k2.metric("Hab / Ing", f"{safe_div(ht, it)*100:.1f}%")
            k3.metric("Ubi / Ing", f"{safe_div(ut, it)*100:.1f}%")
            k4.metric("Rec vs Meta", f"{safe_div(rrt, rmt)*100:.1f}%")

    with t_prod:
        st.markdown("### Productividad por Colaborador")
        if not df_colab.empty:
            df_cf = df_colab[df_colab['Tienda'].isin(sel_s)]
            df_cf['Pzas'] = df_cf['Pzas'].apply(to_num)
            user = df_cf.groupby(['Nombre', 'Tienda'])['Pzas'].sum().reset_index().sort_values('Pzas', ascending=False)
            st.plotly_chart(px.bar(user.head(20), x='Nombre', y='Pzas', color='Tienda', title="Top 20 Productividad"), use_container_width=True)
            st.dataframe(user, use_container_width=True)

    with t_model:
        st.markdown("### Top 30 Modelos (Recuperación)")
        if not df_models.empty:
            df_mf = df_models[(df_models['Semana'].isin(sel_w)) & (df_models['Tienda'].isin(sel_s))]
            top = df_mf.groupby(['Modelo', 'Color', 'Marca']).agg({'Dev': 'sum', 'Venta': 'sum', 'Neta_$': 'sum'}).reset_index()
            top['Recuperadas'] = top[['Dev', 'Venta']].min(axis=1)
            top['Venta_Rec_$'] = top.apply(lambda r: r['Neta_$'] * safe_div(r['Recuperadas'], r['Venta']), axis=1)
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Pzas Devolución", f"{top['Dev'].sum():,.0f}")
            k2.metric("Pzas Recuperadas", f"{top['Recuperadas'].sum():,.0f}", delta=f"{safe_div(top['Recuperadas'].sum(), top['Dev'].sum())*100:.1f}%")
            k3.metric("Venta Neta Rec.", f"${top['Venta_Rec_$'].sum():,.2f}")
            st.dataframe(top.sort_values('Recuperadas', ascending=False).head(30), use_container_width=True)
        else:
            st.warning("No hay datos de modelos para los filtros seleccionados.")

    with t_conv:
        st.markdown("### Tendencia de Conversión")
        if not df_models.empty:
            conv = df_models.groupby('Semana').agg({'Dev': 'sum', 'Venta': 'sum'}).reset_index()
            conv['Rec'] = conv[['Dev', 'Venta']].min(axis=1)
            conv['%'] = conv.apply(lambda r: safe_div(r['Rec'], r['Dev'])*100, axis=1)
            st.plotly_chart(px.line(conv, x='Semana', y='%', markers=True, title="Evolución % Recuperación"), use_container_width=True)

    with t_audit:
        st.dataframe(df_f, use_container_width=True)
else:
    st.info("Conectando con la base de datos ejecutiva...")
