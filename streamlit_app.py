import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO
from datetime import datetime

# =========================================================================
# --- CONFIGURACIÓN ULTRA LIGERA ---
# =========================================================================
st.set_page_config(page_title="Price Shoes BI", layout="wide")

def safe_div(num, den):
    return (num / den) if den and den > 0 else 0

def to_number(series):
    return pd.to_numeric(series.astype(str).str.replace('$', '').str.replace(',', '').str.replace(' ', ''), errors='coerce').fillna(0)

@st.cache_data(ttl=600)
def load_data():
    URL_XLSX = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSd7J_FSk0829VZzHVRn4DoJx-E2CT4iK_nKq026i6B8UaPLeoyX5eRtCXYIaZO2pWGPS4Wd94inFYw/pub?output=xlsx"
    URL_CSV = "https://drive.google.com/uc?export=download&id=15UBabZ8g_VbDMZiPfR2iuW-U9YuNgHWP"
    
    try:
        resp = requests.get(URL_XLSX, timeout=180)
        xls = pd.ExcelFile(BytesIO(resp.content), engine='openpyxl')
        
        all_op = []
        df_models = pd.DataFrame()
        
        # Cargar solo lo necesario de cada hoja
        for sheet in xls.sheet_names:
            if 'sem' in sheet.lower():
                df_s = pd.read_excel(xls, sheet_name=sheet, header=None, engine='openpyxl')
                h_rows = df_s[df_s[1] == 'Tienda'].index.tolist()
                for h_idx in h_rows:
                    fecha = df_s.iloc[h_idx - 1, 1]
                    if not isinstance(fecha, datetime): continue
                    d_idx = h_idx + 1
                    while d_idx < len(df_s) and pd.notna(df_s.iloc[d_idx, 1]):
                        r = df_s.iloc[d_idx, 1:15].tolist()
                        all_op.append({
                            'Tienda': r[0], 'Total_Ing': r[5], 'Meta_Rec': r[6], 'Real_Rec': r[7],
                            'Pzas_Hab': r[9], 'Pzas_Ubi': r[10], 'Semana': sheet
                        })
                        d_idx += 1
            
            if 'venta y devolucion' in sheet.lower():
                # Leer solo las cabeceras primero para optimizar
                df_m_raw = pd.read_excel(xls, sheet_name=sheet, header=None, engine='openpyxl')
                fechas = df_m_raw.iloc[0].tolist()
                cabeceras = df_m_raw.iloc[1].tolist()
                data = df_m_raw.iloc[2:].copy()
                
                # Identificar columnas clave (Modelo, Color, Marca, Tiendas)
                idx_mod = cabeceras.index('Modelo') if 'Modelo' in cabeceras else 4
                idx_col = cabeceras.index('Color') if 'Color' in cabeceras else 7
                idx_mar = cabeceras.index('Marca Price') if 'Marca Price' in cabeceras else 3
                idx_tie = cabeceras.index('Tiendas') if 'Tiendas' in cabeceras else 25
                
                melted = []
                # Procesar bloques de métricas (Ventas, Dev, $)
                for i in range(25, len(cabeceras), 3):
                    if i+2 >= len(cabeceras) or pd.isna(fechas[i]): continue
                    try:
                        f_dt = pd.to_datetime(fechas[i])
                        sem_str = f"Sem {f_dt.isocalendar().week}"
                        
                        subset = data.iloc[:, [idx_mod, idx_col, idx_mar, idx_tie, i, i+1, i+2]].copy()
                        subset.columns = ['Modelo', 'Color', 'Marca', 'Tienda', 'Venta', 'Dev', 'Neta_$']
                        subset['Semana'] = sem_str
                        melted.append(subset)
                    except: continue
                if melted:
                    df_models = pd.concat(melted, ignore_index=True)
                    for c in ['Venta', 'Dev', 'Neta_$']: df_models[c] = to_number(df_models[c])
        
        df_op = pd.DataFrame(all_op)
        if not df_op.empty:
            for c in ['Total_Ing', 'Real_Rec', 'Pzas_Hab', 'Pzas_Ubi', 'Meta_Rec']:
                df_op[c] = pd.to_numeric(df_op[c], errors='coerce').fillna(0)
                
        # Cargar colaboradores (CSV)
        resp_c = requests.get(URL_CSV, timeout=60)
        df_m = pd.read_csv(BytesIO(resp_c.content), encoding='latin1', low_memory=False)
        df_m = df_m.rename(columns={'Ubicación': 'Tienda', 'Numero de Piezas': 'Pzas', 'Número de Piezas': 'Pzas'})
        
        return df_op, df_models, df_m
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_op, df_models, df_m = load_data()

if not df_op.empty:
    st.sidebar.title("Filtros")
    weeks = sorted(df_op['Semana'].unique().tolist())
    sel_w = st.sidebar.multiselect("Semanas", weeks, default=weeks)
    stores = sorted(df_op['Tienda'].unique().tolist())
    sel_s = st.sidebar.multiselect("Tiendas", stores, default=stores)
    
    df_f = df_op[(df_op['Semana'].isin(sel_w)) & (df_op['Tienda'].isin(sel_s))]
    
    st.title("Price Shoes Operational BI")
    
    tab1, tab2, tab3 = st.tabs(["Scorecard", "Top 30 Modelos", "Colaboradores"])
    
    with tab1:
        st.subheader("Consolidado")
        c1, c2, c3, c4 = st.columns(4)
        ing, hab, ubi, rm, rr = df_f['Total_Ing'].sum(), df_f['Pzas_Hab'].sum(), df_f['Pzas_Ubi'].sum(), df_f['Meta_Rec'].sum(), df_f['Real_Rec'].sum()
        c1.metric("Ingresos", f"{ing:,.0f}")
        c2.metric("Hab/Ing", f"{safe_div(hab, ing)*100:.1f}%")
        c3.metric("Ubi/Ing", f"{safe_div(ubi, ing)*100:.1f}%")
        c4.metric("Rec vs Meta", f"{safe_div(rr, rm)*100:.1f}%")
        
        for t in sorted(df_f['Tienda'].unique()):
            d_t = df_f[df_f['Tienda'] == t]
            with st.expander(f"📍 {t}"):
                k1, k2, k3, k4 = st.columns(4)
                i_t, h_t, u_t, rm_t, rr_t = d_t['Total_Ing'].sum(), d_t['Pzas_Hab'].sum(), d_t['Pzas_Ubi'].sum(), d_t['Meta_Rec'].sum(), d_t['Real_Rec'].sum()
                k1.metric("Ingresos", f"{i_t:,.0f}")
                k2.metric("Hab/Ing", f"{safe_div(h_t, i_t)*100:.1f}%")
                k3.metric("Ubi/Ing", f"{safe_div(u_t, i_t)*100:.1f}%")
                k4.metric("Rec vs Meta", f"{safe_div(rr_t, rm_t)*100:.1f}%")

    with tab2:
        st.subheader("Top 30 Modelos (Recuperación)")
        if not df_models.empty:
            df_mf = df_models[(df_models['Semana'].isin(sel_w)) & (df_models['Tienda'].isin(sel_s))]
            grouped = df_mf.groupby(['Modelo', 'Color', 'Marca']).agg({'Dev': 'sum', 'Venta': 'sum', 'Neta_$': 'sum'}).reset_index()
            grouped['Recuperadas'] = grouped[['Dev', 'Venta']].min(axis=1)
            grouped['Venta_Rec_$'] = grouped.apply(lambda r: r['Neta_$'] * safe_div(r['Recuperadas'], r['Venta']), axis=1)
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Pzas Dev", f"{grouped['Dev'].sum():,.0f}")
            k2.metric("Pzas Rec", f"{grouped['Recuperadas'].sum():,.0f}")
            k3.metric("Venta Rec $", f"${grouped['Venta_Rec_$'].sum():,.2f}")
            
            st.dataframe(grouped.sort_values('Recuperadas', ascending=False).head(30), use_container_width=True)

    with tab3:
        if not df_m.empty:
            df_mf = df_m[df_m['Tienda'].isin(sel_s)]
            df_mf['Pzas'] = to_number(df_mf['Pzas'])
            user = df_mf.groupby(['Nombre', 'Tienda'])['Pzas'].sum().reset_index().sort_values('Pzas', ascending=False)
            st.plotly_chart(px.bar(user.head(20), x='Nombre', y='Pzas', color='Tienda'), use_container_width=True)
else:
    st.info("Cargando base de datos... por favor espera.")
