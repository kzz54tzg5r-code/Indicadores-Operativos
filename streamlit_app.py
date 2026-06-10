import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from datetime import datetime
import gc
import time

# =========================================================================
# --- CONFIGURACIÓN DE CARGA PROGRESIVA (v11) ---
# =========================================================================
st.set_page_config(page_title="Price Shoes BI", layout="wide")

def to_num(val):
    try:
        if pd.isna(val): return 0
        return float(str(val).replace('$', '').replace(',', '').replace(' ', ''))
    except: return 0

@st.cache_data(ttl=600)
def load_base_excel():
    """Descarga el archivo Excel una sola vez y lo guarda en cache"""
    URL_XLSX = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSd7J_FSk0829VZzHVRn4DoJx-E2CT4iK_nKq026i6B8UaPLeoyX5eRtCXYIaZO2pWGPS4Wd94inFYw/pub?output=xlsx"
    try:
        resp = requests.get(URL_XLSX, timeout=180)
        return BytesIO(resp.content)
    except Exception as e:
        st.error(f"Error al descargar base de datos: {e}")
        return None

def process_op_data(xls_bytes):
    """Procesa solo los datos del Scorecard (rápido)"""
    all_op = []
    try:
        xls = pd.ExcelFile(xls_bytes, engine='openpyxl')
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
                            'Tienda': str(r[0]), 'Total_Ing': to_num(r[5]), 'Meta_Rec': to_num(r[6]), 
                            'Real_Rec': to_num(r[7]), 'Pzas_Hab': to_num(r[9]), 'Pzas_Ubi': to_num(r[10]), 
                            'Semana': sheet
                        })
                        d_idx += 1
                del df_s
                gc.collect()
        return pd.DataFrame(all_op)
    except:
        return pd.DataFrame()

def process_model_data(xls_bytes):
    """Procesa los datos de modelos (pesado)"""
    try:
        xls = pd.ExcelFile(xls_bytes, engine='openpyxl')
        if 'venta y devolucion' in [s.lower() for s in xls.sheet_names]:
            sheet_name = [s for s in xls.sheet_names if 'venta y devolucion' in s.lower()][0]
            df_m_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None, engine='openpyxl', nrows=3000)
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
                df = pd.concat(melted, ignore_index=True)
                for c in ['Venta', 'Dev', 'Neta_$']: 
                    df[c] = pd.to_numeric(df[c].astype(str).str.replace('$', '').str.replace(',', ''), errors='coerce').fillna(0)
                return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- INICIO DE CARGA ---
st.title("Price Shoes Operational BI")

placeholder = st.empty()
with placeholder.container():
    st.info("🚀 Iniciando conexión con Google Sheets... Por favor espera.")
    progress_bar = st.progress(0)

# Paso 1: Descargar Excel
xls_bytes = load_base_excel()
if xls_bytes:
    progress_bar.progress(30)
    st.info("📦 Base de datos descargada. Procesando Scorecard...")
    
    # Paso 2: Procesar Datos Operativos (Rápido)
    df_op = process_op_data(xls_bytes)
    progress_bar.progress(60)
    
    if not df_op.empty:
        placeholder.empty() # Limpiar mensajes de carga
        
        # --- SIDEBAR ---
        st.sidebar.header("Filtros")
        sel_w = st.sidebar.multiselect("Semanas", sorted(df_op['Semana'].unique()), default=df_op['Semana'].unique())
        sel_s = st.sidebar.multiselect("Tiendas", sorted(df_op['Tienda'].unique()), default=df_op['Tienda'].unique())
        df_f = df_op[(df_op['Semana'].isin(sel_w)) & (df_op['Tienda'].isin(sel_s))]
        
        # --- TABS ---
        t1, t2 = st.tabs(["📈 SCORECARD", "🏆 TOP 30 MODELOS"])
        
        with t1:
            st.subheader("Consolidado Global")
            i, h, u, rm, rr = df_f['Total_Ing'].sum(), df_f['Pzas_Hab'].sum(), df_f['Pzas_Ubi'].sum(), df_f['Meta_Rec'].sum(), df_f['Real_Rec'].sum()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Ingresos", f"{i:,.0f}")
            c2.metric("Hab/Ing", f"{(h/i*100 if i>0 else 0):.1f}%")
            c3.metric("Ubi/Ing", f"{(u/i*100 if i>0 else 0):.1f}%")
            c4.metric("Rec vs Meta", f"{(rr/rm*100 if rm>0 else 0):.1f}%")
            
            st.subheader("Detalle por Tienda")
            for t in sorted(df_f['Tienda'].unique()):
                dt = df_f[df_f['Tienda'] == t]
                with st.expander(f"📍 {t}"):
                    it, ht, ut, rmt, rrt = dt['Total_Ing'].sum(), dt['Pzas_Hab'].sum(), dt['Pzas_Ubi'].sum(), dt['Meta_Rec'].sum(), dt['Real_Rec'].sum()
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("Ing", f"{it:,.0f}")
                    k2.metric("Hab/Ing", f"{(ht/it*100 if it>0 else 0):.1f}%")
                    k3.metric("Ubi/Ing", f"{(ut/it*100 if it>0 else 0):.1f}%")
                    k4.metric("Rec/Meta", f"{(rrt/rmt*100 if rmt>0 else 0):.1f}%")

        with t2:
            st.subheader("Análisis de Recuperación (Venta vs Devolución)")
            if st.button("🔍 Cargar Datos de Modelos (Proceso Pesado)"):
                with st.spinner("Analizando modelos... Esto puede tardar 1-2 minutos."):
                    df_models = process_model_data(xls_bytes)
                    if not df_models.empty:
                        df_mf = df_models[(df_models['Semana'].isin(sel_w)) & (df_models['Tienda'].isin(sel_s))]
                        top = df_mf.groupby(['Modelo', 'Color', 'Marca']).agg({'Dev': 'sum', 'Venta': 'sum', 'Neta_$': 'sum'}).reset_index()
                        top['Recuperadas'] = top[['Dev', 'Venta']].min(axis=1)
                        top['Venta_Rec_$'] = top.apply(lambda r: r['Neta_$'] * (r['Recuperadas']/r['Venta'] if r['Venta']>0 else 0), axis=1)
                        
                        k1, k2, k3 = st.columns(3)
                        k1.metric("Pzas Dev", f"{top['Dev'].sum():,.0f}")
                        k2.metric("Pzas Rec", f"{top['Recuperadas'].sum():,.0f}")
                        k3.metric("Venta Rec $", f"${top['Venta_Rec_$'].sum():,.2f}")
                        st.dataframe(top.sort_values('Recuperadas', ascending=False).head(30), use_container_width=True)
                    else:
                        st.error("No se pudieron cargar los modelos. Verifica que la pestaña 'venta y devolucion' esté publicada.")
            else:
                st.info("Haz clic en el botón de arriba para cargar el análisis de modelos. Se hace por separado para no saturar la memoria.")
    else:
        st.error("No se encontraron datos operativos en el archivo.")
else:
    st.error("No se pudo conectar con la base de datos. Verifica el enlace de publicación.")
