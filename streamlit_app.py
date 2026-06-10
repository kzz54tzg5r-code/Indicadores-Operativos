import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from datetime import datetime
import gc

# =========================================================================
# --- CONFIGURACIÓN DE ALTA DISPONIBILIDAD (v10) ---
# =========================================================================
st.set_page_config(page_title="Price Shoes BI", layout="wide")

def to_num(val):
    try:
        if pd.isna(val): return 0
        return float(str(val).replace('$', '').replace(',', '').replace(' ', ''))
    except: return 0

@st.cache_data(ttl=600)
def load_data_safe():
    URL_XLSX = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSd7J_FSk0829VZzHVRn4DoJx-E2CT4iK_nKq026i6B8UaPLeoyX5eRtCXYIaZO2pWGPS4Wd94inFYw/pub?output=xlsx"
    URL_CSV = "https://drive.google.com/uc?export=download&id=15UBabZ8g_VbDMZiPfR2iuW-U9YuNgHWP"
    
    try:
        resp = requests.get(URL_XLSX, timeout=180)
        xls = pd.ExcelFile(BytesIO(resp.content), engine='openpyxl')
        
        all_op = []
        df_models = pd.DataFrame()
        
        # 1. Procesar hojas operativas (Semanas)
        for sheet in xls.sheet_names:
            if 'sem' in sheet.lower():
                try:
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
                except: continue

        # 2. Procesar hoja de modelos (Venta y Devolución)
        # Intentamos cargar solo las columnas necesarias para ahorrar RAM
        if 'venta y devolucion' in [s.lower() for s in xls.sheet_names]:
            sheet_name = [s for s in xls.sheet_names if 'venta y devolucion' in s.lower()][0]
            try:
                # Leemos solo las primeras 5000 filas para evitar caídas si el archivo es masivo
                df_m_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None, engine='openpyxl', nrows=5000)
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
                del df_m_raw
                gc.collect()
            except: pass

        df_op = pd.DataFrame(all_op)
        
        # 3. Cargar colaboradores (CSV)
        resp_c = requests.get(URL_CSV, timeout=60)
        df_m = pd.read_csv(BytesIO(resp_c.content), encoding='latin1', low_memory=False)
        df_m = df_m.rename(columns={'Ubicación': 'Tienda', 'Numero de Piezas': 'Pzas', 'Número de Piezas': 'Pzas'})
        
        return df_op, df_models, df_m
    except Exception as e:
        st.error(f"Error crítico de carga: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_op, df_models, df_m = load_data_safe()

if not df_op.empty:
    st.sidebar.title("Filtros")
    sel_w = st.sidebar.multiselect("Semanas", sorted(df_op['Semana'].unique()), default=df_op['Semana'].unique())
    sel_s = st.sidebar.multiselect("Tiendas", sorted(df_op['Tienda'].unique()), default=df_op['Tienda'].unique())
    
    df_f = df_op[(df_op['Semana'].isin(sel_w)) & (df_op['Tienda'].isin(sel_s))]
    
    st.title("Price Shoes Operational BI")
    
    t1, t2, t3 = st.tabs(["Scorecard", "Top 30 Modelos", "Colaboradores"])
    
    with t1:
        i, h, u, rm, rr = df_f['Total_Ing'].sum(), df_f['Pzas_Hab'].sum(), df_f['Pzas_Ubi'].sum(), df_f['Meta_Rec'].sum(), df_f['Real_Rec'].sum()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ingresos", f"{i:,.0f}")
        c2.metric("Hab/Ing", f"{(h/i*100 if i>0 else 0):.1f}%")
        c3.metric("Ubi/Ing", f"{(u/i*100 if i>0 else 0):.1f}%")
        c4.metric("Rec vs Meta", f"{(rr/rm*100 if rm>0 else 0):.1f}%")
        
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
            st.warning("Los datos de modelos son demasiado pesados para esta conexión. Intenta filtrar menos semanas.")

    with t3:
        if not df_m.empty:
            df_mf = df_m[df_m['Tienda'].isin(sel_s)]
            df_mf['Pzas'] = pd.to_numeric(df_mf['Pzas'], errors='coerce').fillna(0)
            user = df_mf.groupby(['Nombre', 'Tienda'])['Pzas'].sum().reset_index().sort_values('Pzas', ascending=False)
            st.plotly_chart(px.bar(user.head(20), x='Nombre', y='Pzas', color='Tienda'), use_container_width=True)
else:
    st.info("Conectando con la base de datos...")
