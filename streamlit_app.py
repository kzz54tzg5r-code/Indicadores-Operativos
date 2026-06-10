import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from datetime import datetime
import gc

# =========================================================================
# --- CONFIGURACIÓN DE MEMORIA MÍNIMA (v9) ---
# =========================================================================
st.set_page_config(page_title="Price Shoes BI", layout="wide")

def to_num(val):
    try:
        if pd.isna(val): return 0
        return float(str(val).replace('$', '').replace(',', '').replace(' ', ''))
    except: return 0

@st.cache_data(ttl=600)
def load_and_process_data():
    URL_XLSX = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSd7J_FSk0829VZzHVRn4DoJx-E2CT4iK_nKq026i6B8UaPLeoyX5eRtCXYIaZO2pWGPS4Wd94inFYw/pub?output=xlsx"
    URL_CSV = "https://drive.google.com/uc?export=download&id=15UBabZ8g_VbDMZiPfR2iuW-U9YuNgHWP"
    
    try:
        resp = requests.get(URL_XLSX, timeout=180)
        xls = pd.ExcelFile(BytesIO(resp.content), engine='openpyxl')
        
        all_op = []
        # Para modelos, guardaremos un diccionario de agregados para no saturar RAM
        # Estructura: {(Semana, Tienda, Modelo, Color, Marca): [Dev, Venta, Neta$]}
        model_aggregates = {}
        
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
            
            if 'venta y devolucion' in sheet.lower():
                # Procesamiento ultra-ligero: Leer solo las filas necesarias
                df_m_raw = pd.read_excel(xls, sheet_name=sheet, header=None, engine='openpyxl')
                fechas = df_m_raw.iloc[0].tolist()
                cabeceras = df_m_raw.iloc[1].tolist()
                
                # Mapeo de columnas fijas
                idx_mod = cabeceras.index('Modelo') if 'Modelo' in cabeceras else 4
                idx_col = cabeceras.index('Color') if 'Color' in cabeceras else 7
                idx_mar = cabeceras.index('Marca Price') if 'Marca Price' in cabeceras else 3
                idx_tie = cabeceras.index('Tiendas') if 'Tiendas' in cabeceras else 25
                
                # Procesar cada bloque de 3 columnas (Venta, Dev, $)
                for i in range(25, len(cabeceras), 3):
                    if i+2 >= len(cabeceras) or pd.isna(fechas[i]): continue
                    try:
                        f_dt = pd.to_datetime(fechas[i])
                        sem_label = f"Sem {f_dt.isocalendar().week}"
                        
                        # Extraer solo las columnas del bloque para esta iteración
                        for row_idx in range(2, len(df_m_raw)):
                            row = df_m_raw.iloc[row_idx]
                            mod, col, mar, tie = str(row[idx_mod]), str(row[idx_col]), str(row[idx_mar]), str(row[idx_tie])
                            v, d, n = to_num(row[i]), to_num(row[i+1]), to_num(row[i+2])
                            
                            if v == 0 and d == 0: continue
                            
                            key = (sem_label, tie, mod, col, mar)
                            if key not in model_aggregates:
                                model_aggregates[key] = [0, 0, 0]
                            model_aggregates[key][0] += d
                            model_aggregates[key][1] += v
                            model_aggregates[key][2] += n
                    except: continue
                del df_m_raw
                gc.collect()
        
        # Convertir agregados de modelos a DataFrame final
        model_data_list = []
        for k, v in model_aggregates.items():
            model_data_list.append({
                'Semana': k[0], 'Tienda': k[1], 'Modelo': k[2], 'Color': k[3], 'Marca': k[4],
                'Dev': v[0], 'Venta': v[1], 'Neta_$': v[2]
            })
        df_models = pd.DataFrame(model_data_list)
        df_op = pd.DataFrame(all_op)
        
        # Cargar colaboradores
        resp_c = requests.get(URL_CSV, timeout=60)
        df_m = pd.read_csv(BytesIO(resp_c.content), encoding='latin1', low_memory=False)
        df_m = df_m.rename(columns={'Ubicación': 'Tienda', 'Numero de Piezas': 'Pzas', 'Número de Piezas': 'Pzas'})
        
        return df_op, df_models, df_m
    except Exception as e:
        st.error(f"Error de procesamiento: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_op, df_models, df_m = load_and_process_data()

if not df_op.empty:
    st.sidebar.header("Filtros")
    sel_w = st.sidebar.multiselect("Semanas", sorted(df_op['Semana'].unique()), default=df_op['Semana'].unique())
    sel_s = st.sidebar.multiselect("Tiendas", sorted(df_op['Tienda'].unique()), default=df_op['Tienda'].unique())
    
    df_f = df_op[(df_op['Semana'].isin(sel_w)) & (df_op['Tienda'].isin(sel_s))]
    
    st.title("Price Shoes BI")
    
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
            # Agrupar por modelo para el Top 30
            top = df_mf.groupby(['Modelo', 'Color', 'Marca']).agg({'Dev': 'sum', 'Venta': 'sum', 'Neta_$': 'sum'}).reset_index()
            top['Recuperadas'] = top[['Dev', 'Venta']].min(axis=1)
            top['Venta_Rec_$'] = top.apply(lambda r: r['Neta_$'] * (r['Recuperadas']/r['Venta'] if r['Venta']>0 else 0), axis=1)
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Piezas Dev", f"{top['Dev'].sum():,.0f}")
            k2.metric("Piezas Rec", f"{top['Recuperadas'].sum():,.0f}")
            k3.metric("Venta Rec $", f"${top['Venta_Rec_$'].sum():,.2f}")
            
            st.dataframe(top.sort_values('Recuperadas', ascending=False).head(30), use_container_width=True)

    with t3:
        if not df_m.empty:
            df_mf = df_m[df_m['Tienda'].isin(sel_s)]
            df_mf['Pzas'] = pd.to_numeric(df_mf['Pzas'], errors='coerce').fillna(0)
            user = df_mf.groupby(['Nombre', 'Tienda'])['Pzas'].sum().reset_index().sort_values('Pzas', ascending=False)
            st.plotly_chart(px.bar(user.head(20), x='Nombre', y='Pzas', color='Tienda'), use_container_width=True)
else:
    st.info("Conectando con la base de datos...")
