import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO
from datetime import datetime
import gc

# =========================================================================
# --- CONFIGURACIÓN DE NIVEL BI DIRECTOR (v14) ---
# =========================================================================
st.set_page_config(page_title="Price Shoes BI - Conversion Master", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .main { background-color: #F8F9FB; }
    .main-title { color: #1F497D; font-size: 36px; font-weight: 900; letter-spacing: -1.5px; margin-bottom: 0px; }
    .sub-title { color: #E6007E; font-size: 14px; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 25px; }
    .kpi-master { background-color: white; border-radius: 12px; padding: 18px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border-top: 5px solid #1F497D; text-align: center; }
    .kpi-master-label { color: #666; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }
    .kpi-master-value { color: #1F497D; font-size: 28px; font-weight: 900; }
    .semaforo-verde { color: #28a745; font-weight: 900; }
    .semaforo-amarillo { color: #ffc107; font-weight: 900; }
    .semaforo-rojo { color: #dc3545; font-weight: 900; }
    .store-row { background-color: #f1f3f6; padding: 8px; border-radius: 8px; margin-top: 20px; margin-bottom: 10px; font-weight: bold; color: #1F497D; border-left: 5px solid #1F497D; }
    </style>
    """, unsafe_allow_html=True)

def to_num(val):
    try:
        if pd.isna(val) or val == '': return 0
        return float(str(val).replace('$', '').replace(',', '').replace(' ', ''))
    except: return 0

def safe_div(num, den):
    return (num / den) if den and den > 0 else 0

def get_semaforo_class(val):
    if val >= 80: return "semaforo-verde"
    if val >= 60: return "semaforo-amarillo"
    return "semaforo-rojo"

@st.cache_data(ttl=600)
def load_all_intelligence_data():
    URL_XLSX = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSd7J_FSk0829VZzHVRn4DoJx-E2CT4iK_nKq026i6B8UaPLeoyX5eRtCXYIaZO2pWGPS4Wd94inFYw/pub?output=xlsx"
    meses_dict = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}
    
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
            
            # Mapeo flexible
            rename_map = {
                'Ubicación': 'Tienda', 'Piezas de Ingreso': 'Total_Ing', 
                'Piezas Habilitadas': 'Pzas_Hab', 'Piezas Ubicadas': 'Pzas_Ubi',
                'Recorridos Realizados': 'Real_Rec', 'Meta de Recorridos': 'Meta_Rec'
            }
            df_op = df_b.rename(columns=rename_map)
            
            # Si las columnas no existen, intentar detectarlas por posición
            if 'Tienda' not in df_op.columns and len(df_op.columns) > 3:
                df_op = df_op.rename(columns={df_op.columns[3]: 'Tienda'})
            
            for c in ['Total_Ing', 'Pzas_Hab', 'Pzas_Ubi', 'Real_Rec', 'Meta_Rec']:
                if c not in df_op.columns: df_op[c] = 0
                else: df_op[c] = df_op[c].apply(to_num)
            
            if 'Fecha' in df_op.columns:
                df_op['Fecha_DT'] = pd.to_datetime(df_op['Fecha'], errors='coerce')
                df_op = df_op[df_op['Fecha_DT'].notna()]
                df_op['Semana'] = df_op['Fecha_DT'].dt.isocalendar().week.apply(lambda x: f"Sem {x}")
                df_op['Mes'] = df_op['Fecha_DT'].dt.month.map(meses_dict)
            else:
                df_op['Semana'] = "Sem Actual"
                df_op['Mes'] = "Junio"

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
                    mes_label = meses_dict.get(f_dt.month, "Junio")
                    
                    subset = df_m_raw.iloc[2:, [idx_mod, idx_col, idx_mar, idx_tie, i, i+1, i+2]].copy()
                    subset.columns = ['Modelo', 'Color', 'Marca', 'Tienda', 'Venta', 'Dev', 'Neta_$']
                    subset['Semana'] = sem_label
                    subset['Mes'] = mes_label
                    melted.append(subset)
                except: continue
            if melted:
                df_models = pd.concat(melted, ignore_index=True)
                for c in ['Venta', 'Dev', 'Neta_$']: 
                    df_models[c] = df_models[c].apply(to_num)

        return df_op, df_models
    except Exception as e:
        st.error(f"Error de carga: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_op, df_models = load_all_intelligence_data()

if not df_op.empty:
    st.sidebar.image("https://priceshoes.com/media/logo/stores/1/logo_price_shoes.png", width=160)
    st.sidebar.markdown("### Filtros Globales")
    
    meses_ord = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    meses_disp = [m for m in meses_ord if m in df_op['Mes'].unique()]
    sel_m = st.sidebar.multiselect("Meses:", meses_disp, default=meses_disp)
    
    weeks = sorted([w for w in df_op['Semana'].unique() if str(w) != 'nan'])
    sel_w = st.sidebar.multiselect("Semanas:", weeks, default=weeks[-1:] if weeks else [])
    
    stores = sorted([t for t in df_op['Tienda'].unique() if str(t) != 'nan'])
    sel_s = st.sidebar.multiselect("Tiendas:", stores, default=stores)
    
    df_f = df_op[(df_op['Mes'].isin(sel_m)) & (df_op['Semana'].isin(sel_w)) & (df_op['Tienda'].isin(sel_s))]
    df_mf = df_models[(df_models['Mes'].isin(sel_m)) & (df_models['Semana'].isin(sel_w)) & (df_models['Tienda'].isin(sel_s))] if not df_models.empty else pd.DataFrame()

    st.markdown('<p class="main-title">PRICE SHOES • Operational Intelligence Center</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">SISTEMA DE CONTROL DE CONVERSIÓN Y RECUPERACIÓN</p>', unsafe_allow_html=True)

    # --- TABS ---
    t_exec, t_conv, t_model, t_audit = st.tabs(["📊 SCORECARD", "📈 CONVERSIÓN SEMANAL", "🏆 TOP 30 MODELOS", "📋 AUDITORÍA"])

    with t_exec:
        st.markdown("### Resumen Ejecutivo de Conversión")
        if not df_mf.empty:
            # Cálculos de conversión
            total_dev = df_mf['Dev'].sum()
            total_venta = df_mf['Venta'].sum()
            total_rec_pzas = df_mf.groupby(['Modelo', 'Color', 'Marca', 'Tienda']).apply(lambda x: min(x['Dev'].sum(), x['Venta'].sum())).sum()
            
            # Valor de recuperación
            df_mf['Rec_Pzas'] = df_mf.apply(lambda r: min(r['Dev'], r['Venta']), axis=1)
            df_mf['Val_Rec_$'] = df_mf.apply(lambda r: r['Neta_$'] * safe_div(r['Rec_Pzas'], r['Venta']), axis=1)
            val_total_rec = df_mf['Val_Rec_$'].sum()
            val_pendiente = (df_mf['Neta_$'].sum() - val_total_rec) if total_venta > total_dev else 0
            
            conv_gen = safe_div(total_rec_pzas, total_dev) * 100
            
            # Tiendas mejor/peor
            tienda_stats = df_mf.groupby('Tienda').apply(lambda x: safe_div(min(x['Dev'].sum(), x['Venta'].sum()), x['Dev'].sum()) * 100).reset_index(name='Conv')
            mejor_t = tienda_stats.sort_values('Conv', ascending=False).iloc[0] if not tienda_stats.empty else None
            peor_t = tienda_stats.sort_values('Conv', ascending=True).iloc[0] if not tienda_stats.empty else None

            c1, c2, c3, c4, c5 = st.columns(5)
            with c1: st.markdown(f'<div class="kpi-master"><p class="kpi-master-label">Conversión Gral.</p><p class="kpi-master-value {get_semaforo_class(conv_gen)}">{conv_gen:.1f}%</p></div>', unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="kpi-master"><p class="kpi-master-label">Mejor Tienda</p><p class="kpi-master-value" style="font-size:18px">{mejor_t["Tienda"] if mejor_t is not None else "N/A"}</p><p style="color:#28a745; font-weight:bold">{mejor_t["Conv"]:.1f}%</p></div>', unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="kpi-master"><p class="kpi-master-label">Peor Tienda</p><p class="kpi-master-value" style="font-size:18px">{peor_t["Tienda"] if peor_t is not None else "N/A"}</p><p style="color:#dc3545; font-weight:bold">{peor_t["Conv"]:.1f}%</p></div>', unsafe_allow_html=True)
            with c4: st.markdown(f'<div class="kpi-master"><p class="kpi-master-label">Valor Recuperado</p><p class="kpi-master-value">${val_total_rec:,.0f}</p></div>', unsafe_allow_html=True)
            with c5: st.markdown(f'<div class="kpi-master"><p class="kpi-master-label">Valor Pendiente</p><p class="kpi-master-value">${val_pendiente:,.0f}</p></div>', unsafe_allow_html=True)
        else:
            st.warning("No hay datos de modelos para calcular la conversión ejecutiva.")

        st.markdown("### Scorecard por Tienda")
        i_t, h_t, u_t, rm_t, rr_t = df_f['Total_Ing'].sum(), df_f['Pzas_Hab'].sum(), df_f['Pzas_Ubi'].sum(), df_f['Meta_Rec'].sum(), df_f['Real_Rec'].sum()
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Ingresos Totales", f"{i_t:,.0f}")
        k2.metric("Hab / Ing", f"{safe_div(h_t, i_t) * 100:.1f}%")
        k3.metric("Ubi / Ing", f"{safe_div(u_t, i_t) * 100:.1f}%")
        k4.metric("Rec vs Meta", f"{safe_div(rr_t, rm_t) * 100:.1f}%")

    with t_conv:
        st.markdown("### Análisis de Conversión por Tienda")
        if not df_mf.empty:
            tienda_conv = df_mf.groupby('Tienda').agg({'Dev': 'sum', 'Venta': 'sum', 'Val_Rec_$': 'sum', 'Neta_$': 'sum'}).reset_index()
            tienda_conv['Rec_Pzas'] = tienda_conv.apply(lambda r: min(r['Dev'], r['Venta']), axis=1)
            tienda_conv['Conv_%'] = tienda_conv.apply(lambda r: safe_div(r['Rec_Pzas'], r['Dev']) * 100, axis=1)
            tienda_conv['Pzas_Pend'] = (tienda_conv['Dev'] - tienda_conv['Rec_Pzas']).clip(lower=0)
            tienda_conv['Val_Pend_$'] = (tienda_conv['Neta_$'] - tienda_conv['Val_Rec_$']).clip(lower=0)
            
            st.plotly_chart(px.bar(tienda_conv.sort_values('Conv_%', ascending=False), x='Tienda', y='Conv_%', color='Conv_%', 
                                   color_continuous_scale=['red', 'yellow', 'green'], title="Ranking de Tiendas por Conversión"), use_container_width=True)
            
            st.dataframe(tienda_conv[['Tienda', 'Dev', 'Venta', 'Conv_%', 'Pzas_Pend', 'Val_Rec_$', 'Val_Pend_$']].sort_values('Conv_%', ascending=False), use_container_width=True)
        
        st.markdown("### Tendencia Semanal de Conversión")
        if not df_models.empty:
            sem_conv = df_models.groupby('Semana').agg({'Dev': 'sum', 'Venta': 'sum'}).reset_index()
            sem_conv['Rec'] = sem_conv.apply(lambda r: min(r['Dev'], r['Venta']), axis=1)
            sem_conv['Conv_%'] = sem_conv.apply(lambda r: safe_div(r['Rec'], r['Dev']) * 100, axis=1)
            st.plotly_chart(px.line(sem_conv, x='Semana', y='Conv_%', markers=True, title="Evolución Semanal de Conversión %"), use_container_width=True)

    with t_model:
        st.markdown("### Top 30 Modelos (Efectividad de Recuperación)")
        if not df_mf.empty:
            top_mod = df_mf.groupby(['Modelo', 'Color', 'Marca']).agg({'Dev': 'sum', 'Venta': 'sum', 'Val_Rec_$': 'sum'}).reset_index()
            top_mod['Rec_Pzas'] = top_mod.apply(lambda r: min(r['Dev'], r['Venta']), axis=1)
            top_mod['Conv_%'] = top_mod.apply(lambda r: safe_div(r['Rec_Pzas'], r['Dev']) * 100, axis=1)
            st.dataframe(top_mod.sort_values(['Rec_Pzas', 'Val_Rec_$'], ascending=False).head(30), use_container_width=True)
        else:
            st.warning("No hay datos de modelos disponibles.")

    with t_audit:
        st.markdown("### Datos Crudos de Operación")
        st.dataframe(df_f, use_container_width=True)
else:
    st.info("Conectando con la base de datos de Price Shoes... Por favor espera.")
