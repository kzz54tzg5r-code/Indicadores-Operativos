import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from datetime import datetime
import gc

# =========================================================================
# --- CONFIGURACIÓN DE ADAPTACIÓN REAL (v12) ---
# =========================================================================
st.set_page_config(page_title="Price Shoes BI", layout="wide")

def to_num(val):
    try:
        if pd.isna(val) or val == '': return 0
        return float(str(val).replace('$', '').replace(',', '').replace(' ', ''))
    except: return 0

@st.cache_data(ttl=600)
def load_excel_data():
    URL_XLSX = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSd7J_FSk0829VZzHVRn4DoJx-E2CT4iK_nKq026i6B8UaPLeoyX5eRtCXYIaZO2pWGPS4Wd94inFYw/pub?output=xlsx"
    try:
        resp = requests.get(URL_XLSX, timeout=180)
        return BytesIO(resp.content)
    except: return None

def process_all(xls_bytes):
    df_op = pd.DataFrame()
    df_models = pd.DataFrame()
    
    try:
        xls = pd.ExcelFile(xls_bytes, engine='openpyxl')
        sheets = xls.sheet_names
        
        # 1. Procesar Datos Operativos (de la pestaña 'Base de datos muertos y cambios')
        # Buscamos la pestaña que contenga "base de datos"
        base_sheet = [s for s in sheets if 'base de datos' in s.lower()]
        if base_sheet:
            df_b = pd.read_excel(xls, sheet_name=base_sheet[0], engine='openpyxl')
            # Limpiar nombres de columnas
            df_b.columns = [str(c).strip() for c in df_b.columns]
            
            # Mapeo según estructura común de Price Shoes
            # Si no hay columnas estándar, intentamos identificar por contenido
            df_op = df_b.copy()
            # Asegurar columnas mínimas para el Scorecard
            if 'Ubicación' in df_op.columns: df_op = df_op.rename(columns={'Ubicación': 'Tienda'})
            elif 'Tienda' not in df_op.columns and len(df_op.columns) > 3: df_op = df_op.rename(columns={df_op.columns[3]: 'Tienda'})
            
            # Si no hay métricas, las creamos como 0 para que no falle la UI
            for c in ['Total_Ing', 'Pzas_Hab', 'Pzas_Ubi', 'Meta_Rec', 'Real_Rec']:
                if c not in df_op.columns: df_op[c] = 0
            
            # Extraer Semana de la fecha si existe
            if 'Fecha' in df_op.columns:
                df_op['Fecha'] = pd.to_datetime(df_op['Fecha'], errors='coerce')
                df_op['Semana'] = df_op['Fecha'].dt.isocalendar().week.apply(lambda x: f"Sem {x}")
            else:
                df_op['Semana'] = "Sem Actual"

        # 2. Procesar Modelos (de la pestaña 'Venta y devolucion')
        model_sheet = [s for s in sheets if 'venta y devolucion' in s.lower()]
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
                    df_models[c] = pd.to_numeric(df_models[c].astype(str).str.replace('$', '').str.replace(',', ''), errors='coerce').fillna(0)
        
        return df_op, df_models
    except Exception as e:
        st.error(f"Error procesando: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- UI ---
st.title("Price Shoes BI • Operational Master")

xls_bytes = load_excel_data()
if xls_bytes:
    df_op, df_models = process_all(xls_bytes)
    
    if not df_op.empty:
        # Filtros
        st.sidebar.header("Filtros")
        weeks = sorted(df_op['Semana'].unique()) if 'Semana' in df_op.columns else ["Actual"]
        sel_w = st.sidebar.multiselect("Semanas", weeks, default=weeks)
        stores = sorted(df_op['Tienda'].unique()) if 'Tienda' in df_op.columns else ["General"]
        sel_s = st.sidebar.multiselect("Tiendas", stores, default=stores)
        
        # Filtrado
        df_f = df_op
        if 'Semana' in df_op.columns: df_f = df_f[df_f['Semana'].isin(sel_w)]
        if 'Tienda' in df_op.columns: df_f = df_f[df_f['Tienda'].isin(sel_s)]

        t1, t2 = st.tabs(["📊 SCORECARD", "🏷️ TOP 30 MODELOS"])
        
        with t1:
            st.subheader("Indicadores de Gestión")
            i, h, u, rm, rr = to_num(df_f['Total_Ing'].sum()), to_num(df_f['Pzas_Hab'].sum()), to_num(df_f['Pzas_Ubi'].sum()), to_num(df_f['Meta_Rec'].sum()), to_num(df_f['Real_Rec'].sum())
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Ingresos", f"{i:,.0f}")
            c2.metric("Hab/Ing", f"{(h/i*100 if i>0 else 0):.1f}%")
            c3.metric("Ubi/Ing", f"{(u/i*100 if i>0 else 0):.1f}%")
            c4.metric("Rec vs Meta", f"{(rr/rm*100 if rm>0 else 0):.1f}%")
            
            if 'Tienda' in df_f.columns:
                for t in sorted(df_f['Tienda'].unique()):
                    dt = df_f[df_f['Tienda'] == t]
                    with st.expander(f"📍 {t}"):
                        it, ht, ut, rmt, rrt = to_num(dt['Total_Ing'].sum()), to_num(dt['Pzas_Hab'].sum()), to_num(dt['Pzas_Ubi'].sum()), to_num(dt['Meta_Rec'].sum()), to_num(dt['Real_Rec'].sum())
                        k1, k2, k3, k4 = st.columns(4)
                        k1.metric("Ing", f"{it:,.0f}")
                        k2.metric("Hab/Ing", f"{(ht/it*100 if it>0 else 0):.1f}%")
                        k3.metric("Ubi/Ing", f"{(ut/it*100 if it>0 else 0):.1f}%")
                        k4.metric("Rec/Meta", f"{(rrt/rmt*100 if rmt>0 else 0):.1f}%")

        with t2:
            st.subheader("Recuperación: Venta vs Devolución")
            if not df_models.empty:
                df_mf = df_models
                if sel_w: df_mf = df_mf[df_mf['Semana'].isin(sel_w)]
                if sel_s: df_mf = df_mf[df_mf['Tienda'].isin(sel_s)]
                
                top = df_mf.groupby(['Modelo', 'Color', 'Marca']).agg({'Dev': 'sum', 'Venta': 'sum', 'Neta_$': 'sum'}).reset_index()
                top['Recuperadas'] = top[['Dev', 'Venta']].min(axis=1)
                top['Venta_Rec_$'] = top.apply(lambda r: r['Neta_$'] * (r['Recuperadas']/r['Venta'] if r['Venta']>0 else 0), axis=1)
                
                k1, k2, k3 = st.columns(3)
                k1.metric("Pzas Dev", f"{top['Dev'].sum():,.0f}")
                k2.metric("Pzas Rec", f"{top['Recuperadas'].sum():,.0f}")
                k3.metric("Venta Rec $", f"${top['Venta_Rec_$'].sum():,.2f}")
                st.dataframe(top.sort_values('Recuperadas', ascending=False).head(30), use_container_width=True)
            else:
                st.warning("No se encontraron datos en 'Venta y devolucion'.")
    else:
        st.warning("El archivo no contiene las pestañas esperadas de Semanas. Se intentó leer de 'Base de datos muertos y cambios'.")
else:
    st.error("No se pudo conectar con la base de datos.")
