import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
from io import BytesIO
from datetime import datetime
import numpy as np

# =========================================================================
# --- CONFIGURACIÓN DE NIVEL BI DIRECTOR ---
# =========================================================================
st.set_page_config(page_title="Price Shoes BI - Ultimate Master Center", layout="wide", page_icon="📈")

# Estilos simplificados para mayor estabilidad
st.markdown("""
    <style>
    .main { background-color: #F8F9FB; }
    .kpi-card { background-color: white; border-radius: 10px; padding: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); text-align: center; border-top: 4px solid #1F497D; }
    .kpi-label { color: #666; font-size: 12px; font-weight: bold; text-transform: uppercase; }
    .kpi-value { color: #1F497D; font-size: 24px; font-weight: 900; }
    .store-header { background-color: #f1f3f6; padding: 10px; border-radius: 5px; margin-top: 15px; font-weight: bold; color: #1F497D; }
    </style>
    """, unsafe_allow_html=True)


def safe_div(num, den):
    return (num / den) if den and den > 0 else 0


def to_number(series):
    return pd.to_numeric(
        series.astype(str)
        .str.replace('$', '', regex=False)
        .str.replace(',', '', regex=False)
        .str.replace(' ', '', regex=False),
        errors='coerce'
    ).fillna(0)

@st.cache_data(ttl=600)
def load_all_intelligence_data():
    URL_XLSX = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSd7J_FSk0829VZzHVRn4DoJx-E2CT4iK_nKq026i6B8UaPLeoyX5eRtCXYIaZO2pWGPS4Wd94inFYw/pub?output=xlsx"
    URL_CSV = "https://drive.google.com/uc?export=download&id=15UBabZ8g_VbDMZiPfR2iuW-U9YuNgHWP"
    meses_dict = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}

    try:
        resp_x = requests.get(URL_XLSX, timeout=180)
        resp_x.raise_for_status()
        xls = pd.ExcelFile(BytesIO(resp_x.content), engine='openpyxl')

        all_op = []
        df_models = pd.DataFrame()

        for sheet in xls.sheet_names:
            if 'sem' in sheet.lower():
                raw = pd.read_excel(xls, sheet_name=sheet, header=None, engine='openpyxl')
                h_rows = raw[raw[1] == 'Tienda'].index.tolist()
                for h_idx in h_rows:
                    fecha = raw.iloc[h_idx - 1, 1]
                    if not isinstance(fecha, datetime): 
                        try: fecha = pd.to_datetime(fecha)
                        except: continue
                    if pd.isna(fecha): continue
                    
                    d_idx = h_idx + 1
                    while d_idx < len(raw) and pd.notna(raw.iloc[d_idx, 1]):
                        r = raw.iloc[d_idx, 1:15].tolist()
                        all_op.append({
                            'Tienda': r[0], 'Total_Ing': r[5], 'Meta_Rec': r[6], 'Real_Rec': r[7],
                            'Pzas_Hab': r[9], 'Pzas_Ubi': r[10], 'Fecha': fecha, 'Semana': sheet
                        })
                        d_idx += 1

            if 'venta y devolucion' in sheet.lower():
                df_raw = pd.read_excel(xls, sheet_name=sheet, header=None, engine='openpyxl')
                fechas_raw = df_raw.iloc[0].tolist()
                cabeceras = df_raw.iloc[1].tolist()
                data = df_raw.iloc[2:].copy()
                
                # Columnas de identificación (primeras 25)
                base_cols = cabeceras[:25]
                # Limpiar nombres de columnas base
                base_cols = [str(c).strip() for c in base_cols]
                
                melted_data = []
                for i in range(25, len(cabeceras), 3):
                    if i+2 >= len(cabeceras): break
                    fecha_val = fechas_raw[i]
                    if pd.isna(fecha_val): continue
                    
                    try:
                        fecha_dt = pd.to_datetime(fecha_val)
                        if pd.isna(fecha_dt): continue
                    except: continue
                    
                    subset = data.iloc[:, list(range(25)) + [i, i+1, i+2]].copy()
                    subset.columns = base_cols + ['Ventas_Pzas', 'Dev_Pzas', 'Venta_Neta_$']
                    subset['Fecha_Ref'] = fecha_dt
                    melted_data.append(subset)
                
                if melted_data:
                    df_models = pd.concat(melted_data, ignore_index=True)
                    df_models['Ventas_Pzas'] = to_number(df_models['Ventas_Pzas'])
                    df_models['Dev_Pzas'] = to_number(df_models['Dev_Pzas'])
                    df_models['Venta_Neta_$'] = to_number(df_models['Venta_Neta_$'])
                    df_models['Semana_Ref'] = df_models['Fecha_Ref'].dt.isocalendar().week.apply(lambda x: f"Sem {x}")

        df_op = pd.DataFrame(all_op)
        if not df_op.empty:
            for c in ['Total_Ing', 'Real_Rec', 'Pzas_Hab', 'Pzas_Ubi', 'Meta_Rec']:
                df_op[c] = pd.to_numeric(df_op[c], errors='coerce').fillna(0)
            df_op['Fecha'] = pd.to_datetime(df_op['Fecha'], errors='coerce')
            df_op['Mes'] = df_op['Fecha'].dt.month.map(meses_dict)

        # Cargar base de colaboradores
        resp_c = requests.get(URL_CSV, timeout=60)
        resp_c.raise_for_status()
        df_m = pd.read_csv(BytesIO(resp_c.content), encoding='latin1', low_memory=False)
        df_m.columns = [str(c).strip() for c in df_m.columns]
        df_m = df_m.rename(columns={'Ubicación': 'Tienda', 'Numero de Piezas': 'Pzas', 'Número de Piezas': 'Pzas', 'Actividad Realizada': 'Actividad'})
        df_m['Fecha_DT'] = pd.to_datetime(df_m['Fecha'], errors='coerce') if 'Fecha' in df_m.columns else pd.NaT
        df_m['Mes'] = df_m['Fecha_DT'].dt.month.map(meses_dict)

        return df_op, df_models, df_m
    except Exception as e:
        st.error(f"Error BI: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


def summarize_recovery(df, group_cols):
    if df.empty: return pd.DataFrame()
    grouped = df.groupby(group_cols, dropna=False).agg({'Dev_Pzas': 'sum', 'Ventas_Pzas': 'sum', 'Venta_Neta_$': 'sum'}).reset_index()
    grouped['Pzas_Recuperadas'] = grouped[['Dev_Pzas', 'Ventas_Pzas']].min(axis=1)
    grouped['Venta_Neta_Recuperada_$'] = grouped.apply(lambda r: r['Venta_Neta_$'] * safe_div(r['Pzas_Recuperadas'], r['Ventas_Pzas']) if r['Ventas_Pzas'] > 0 else 0, axis=1)
    grouped['% Recuperacion Dev vs Venta'] = grouped.apply(lambda r: safe_div(r['Pzas_Recuperadas'], r['Dev_Pzas']) * 100, axis=1)
    return grouped


df_op, df_models, df_m = load_all_intelligence_data()

if not df_op.empty:
    st.sidebar.image("https://priceshoes.com/media/logo/stores/1/logo_price_shoes.png", width=160)
    st.sidebar.markdown("### Filtros")
    
    all_weeks = sorted(df_op['Semana'].dropna().unique().tolist(), key=lambda x: int(''.join(filter(str.isdigit, str(x))) or 0))
    sel_semanas = st.sidebar.multiselect("Semanas:", all_weeks, default=all_weeks)
    sel_tiendas = st.sidebar.multiselect("Tiendas:", sorted(df_op['Tienda'].dropna().unique().tolist()), default=df_op['Tienda'].dropna().unique().tolist())
    
    df_f = df_op[(df_op['Tienda'].isin(sel_tiendas)) & (df_op['Semana'].isin(sel_semanas))]

    st.title("Price Shoes BI • Operational Center")

    # --- TABS ---
    t_exec, t_prod, t_model, t_conv = st.tabs(["SCORECARD", "COLABORADORES", "TOP 30 MODELOS", "CONVERSIÓN"])

    with t_exec:
        st.subheader("Consolidado Global")
        ing_t, hab_t, ubi_t, rec_m, rec_r = df_f['Total_Ing'].sum(), df_f['Pzas_Hab'].sum(), df_f['Pzas_Ubi'].sum(), df_f['Meta_Rec'].sum(), df_f['Real_Rec'].sum()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ingresos", f"{ing_t:,.0f}")
        c2.metric("Hab / Ing", f"{safe_div(hab_t, ing_t) * 100:.1f}%")
        c3.metric("Ubi / Ing", f"{safe_div(ubi_t, ing_t) * 100:.1f}%")
        c4.metric("Rec vs Meta", f"{safe_div(rec_r, rec_m) * 100:.1f}%")
        
        st.subheader("Desglose por Tienda")
        for tienda in sorted(df_f['Tienda'].unique()):
            df_t = df_f[df_f['Tienda'] == tienda]
            ing_s, hab_s, ubi_s, rec_ms, rec_rs = df_t['Total_Ing'].sum(), df_t['Pzas_Hab'].sum(), df_t['Pzas_Ubi'].sum(), df_t['Meta_Rec'].sum(), df_t['Real_Rec'].sum()
            with st.expander(f"📍 {tienda}", expanded=True):
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Ingresos", f"{ing_s:,.0f}")
                k2.metric("Hab / Ing", f"{safe_div(hab_s, ing_s)*100:.1f}%")
                k3.metric("Ubi / Ing", f"{safe_div(ubi_s, ing_s)*100:.1f}%")
                k4.metric("Rec vs Meta", f"{safe_div(rec_rs, rec_ms)*100:.1f}%")

    with t_prod:
        st.subheader("Productividad por Colaborador")
        if not df_m.empty:
            df_m_f = df_m[(df_m['Tienda'].isin(sel_tiendas))]
            df_m_f['Pzas'] = to_number(df_m_f['Pzas'])
            df_user = df_m_f.groupby(['Nombre', 'Tienda']).agg({'Pzas': 'sum'}).reset_index().sort_values('Pzas', ascending=False)
            st.plotly_chart(px.bar(df_user.head(20), x='Nombre', y='Pzas', color='Tienda', title="Top 20 Colaboradores"), use_container_width=True)
            st.dataframe(df_user, use_container_width=True)

    with t_model:
        st.subheader("Top 30 Modelos (Recuperación)")
        if not df_models.empty:
            df_mf = df_models.copy()
            # Filtrar por semanas seleccionadas
            if sel_semanas:
                df_mf = df_mf[df_mf['Semana_Ref'].isin(sel_semanas)]
            
            # El archivo tiene la columna 'Tiendas'
            if 'Tiendas' in df_mf.columns:
                tiendas_m = sorted(df_mf['Tiendas'].dropna().unique().tolist())
                sel_t_m = st.selectbox("Tienda (Modelos):", ["Todas"] + tiendas_m)
                if sel_t_m != "Todas":
                    df_mf = df_mf[df_mf['Tiendas'] == sel_t_m]
            
            # Agrupar por Modelo, Color y Marca
            df_top = summarize_recovery(df_mf, ['Modelo', 'Color', 'Marca Price'])
            t_dev, t_venta, t_rec, t_neta_rec = df_top['Dev_Pzas'].sum(), df_top['Ventas_Pzas'].sum(), df_top['Pzas_Recuperadas'].sum(), df_top['Venta_Neta_Recuperada_$'].sum()
            
            st.info("💡 **Lógica de Recuperación:** La venta neta se limita a la cantidad de piezas devueltas.")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Pzas Devolución", f"{t_dev:,.0f}")
            k2.metric("Pzas Vendidas", f"{t_venta:,.0f}")
            k3.metric("Pzas Recuperadas", f"{t_rec:,.0f}", delta=f"{safe_div(t_rec, t_dev)*100:.1f}%")
            k4.metric("Venta Neta Rec.", f"${t_neta_rec:,.2f}")
            
            st.dataframe(df_top.sort_values(['Pzas_Recuperadas', 'Venta_Neta_Recuperada_$'], ascending=False).head(30), use_container_width=True)
        else:
            st.warning("No se encontraron datos en la pestaña 'venta y devolucion'.")

    with t_conv:
        st.subheader("Tendencia de Conversión")
        if not df_models.empty:
            df_c_s = summarize_recovery(df_models, ['Semana_Ref']).sort_values('Semana_Ref')
            st.plotly_chart(px.line(df_c_s, x='Semana_Ref', y='% Recuperacion Dev vs Venta', markers=True), use_container_width=True)
            st.dataframe(df_c_s, use_container_width=True)

else: st.info("Conectando con la base de datos...")
