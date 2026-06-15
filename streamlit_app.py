import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from io import BytesIO
from datetime import datetime
import gc

# =========================================================================
# --- PRICE SHOES RECOVERY INTELLIGENCE PLATFORM (v15 Enterprise) ---
# =========================================================================
st.set_page_config(page_title="Price Shoes Recovery BI", layout="wide", page_icon="📈")

# Diseño Corporativo Avanzado
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main { background-color: #F4F7F9; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 5px solid #1F497D; }
    .exec-card { background: linear-gradient(135deg, #1F497D 0%, #16355C 100%); color: white; padding: 20px; border-radius: 12px; text-align: center; }
    .exec-label { font-size: 12px; text-transform: uppercase; opacity: 0.8; font-weight: bold; }
    .exec-value { font-size: 32px; font-weight: 900; margin: 10px 0; }
    .alert-card { padding: 10px; border-radius: 8px; margin-bottom: 10px; border-left: 5px solid; }
    .alert-high { background-color: #FEE2E2; border-color: #EF4444; color: #991B1B; }
    .alert-mid { background-color: #FEF3C7; border-color: #F59E0B; color: #92400E; }
    .section-title { color: #1F497D; font-size: 24px; font-weight: 900; border-bottom: 3px solid #E6007E; padding-bottom: 5px; margin: 20px 0; }
    </style>
    """, unsafe_allow_html=True)

# --- UTILIDADES ---
def to_num(val):
    try:
        if pd.isna(val) or val == '': return 0
        return float(str(val).replace('$', '').replace(',', '').replace(' ', ''))
    except: return 0

def safe_div(num, den):
    return (num / den) if den and den > 0 else 0

# --- CARGA DE DATOS ---
@st.cache_data(ttl=600)
def load_enterprise_data():
    URL_XLSX = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSd7J_FSk0829VZzHVRn4DoJx-E2CT4iK_nKq026i6B8UaPLeoyX5eRtCXYIaZO2pWGPS4Wd94inFYw/pub?output=xlsx"
    URL_COLAB = "https://drive.google.com/uc?export=download&id=15UBabZ8g_VbDMZiPfR2iuW-U9YuNgHWP"
    
    try:
        resp = requests.get(URL_XLSX, timeout=180)
        xls = pd.ExcelFile(BytesIO(resp.content), engine='openpyxl')
        
        # 1. Pilar Operativo
        sheet_op = [s for s in xls.sheet_names if 'base de datos' in s.lower()]
        df_op = pd.read_excel(xls, sheet_name=sheet_op[0], engine='openpyxl') if sheet_op else pd.DataFrame()
        if not df_op.empty:
            df_op.columns = [str(c).strip() for c in df_op.columns]
            df_op = df_op.rename(columns={
                'Ubicación': 'Tienda', 'Piezas de Ingreso': 'Total_Ing', 
                'Piezas Habilitadas': 'Pzas_Hab', 'Piezas Ubicadas': 'Pzas_Ubi',
                'Recorridos Realizados': 'Real_Rec', 'Meta de Recorridos': 'Meta_Rec'
            })
            for c in ['Total_Ing', 'Pzas_Hab', 'Pzas_Ubi', 'Real_Rec', 'Meta_Rec']:
                if c in df_op.columns: df_op[c] = df_op[c].apply(to_num)
            if 'Fecha' in df_op.columns:
                df_op['Fecha_DT'] = pd.to_datetime(df_op['Fecha'], errors='coerce')
                df_op['Semana'] = df_op['Fecha_DT'].dt.isocalendar().week.apply(lambda x: f"Sem {x}")
                df_op['Mes'] = df_op['Fecha_DT'].dt.month_name()

        # 2. Pilar de Modelos y Conversión
        sheet_mod = [s for s in xls.sheet_names if 'venta y devolucion' in s.lower()]
        df_models = pd.DataFrame()
        if sheet_mod:
            raw_m = pd.read_excel(xls, sheet_name=sheet_mod[0], header=None, engine='openpyxl', nrows=2000)
            fechas, cabs = raw_m.iloc[0].tolist(), raw_m.iloc[1].tolist()
            idx_mod, idx_col, idx_mar, idx_tie = cabs.index('Modelo'), cabs.index('Color'), cabs.index('Marca Price'), cabs.index('Tiendas')
            melted = []
            for i in range(25, len(cabs), 3):
                if i+2 >= len(cabs) or pd.isna(fechas[i]): continue
                try:
                    f_dt = pd.to_datetime(fechas[i])
                    subset = raw_m.iloc[2:, [idx_mod, idx_col, idx_mar, idx_tie, i, i+1, i+2]].copy()
                    subset.columns = ['Modelo', 'Color', 'Marca', 'Tienda', 'Venta', 'Dev', 'Neta_$']
                    subset['Semana'] = f"Sem {f_dt.isocalendar().week}"
                    melted.append(subset)
                except: continue
            if melted:
                df_models = pd.concat(melted, ignore_index=True)
                for c in ['Venta', 'Dev', 'Neta_$']: df_models[c] = df_models[c].apply(to_num)

        # 3. Pilar de Productividad (Colaboradores)
        resp_c = requests.get(URL_COLAB, timeout=60)
        df_colab = pd.read_csv(BytesIO(resp_c.content), encoding='latin1', low_memory=False)
        df_colab = df_colab.rename(columns={'Ubicación': 'Tienda', 'Numero de Piezas': 'Pzas', 'Número de Piezas': 'Pzas'})
        df_colab['Pzas'] = df_colab['Pzas'].apply(to_num)

        return df_op, df_models, df_colab
    except Exception as e:
        st.error(f"Error de Arquitectura: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_op, df_models, df_colab = load_enterprise_data()

# --- INTERFAZ ---
if not df_op.empty:
    # Sidebar
    st.sidebar.title("🎛️ Control Center")
    weeks = sorted([w for w in df_op['Semana'].unique() if str(w) != 'nan'])
    sel_w = st.sidebar.multiselect("Semanas", weeks, default=weeks[-1:] if weeks else [])
    stores = sorted([t for t in df_op['Tienda'].unique() if str(t) != 'nan'])
    sel_s = st.sidebar.multiselect("Tiendas", stores, default=stores)

    df_f = df_op[(df_op['Semana'].isin(sel_w)) & (df_op['Tienda'].isin(sel_s))]
    df_mf = df_models[(df_models['Semana'].isin(sel_w)) & (df_models['Tienda'].isin(sel_s))] if not df_models.empty else pd.DataFrame()
    df_cf = df_colab[df_colab['Tienda'].isin(sel_s)]

    # Header
    st.markdown('<p class="main-title">Price Shoes Recovery Intelligence</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Enterprise BI Platform • National Operation Control</p>', unsafe_allow_html=True)

    tabs = st.tabs(["🚀 RESUMEN EJECUTIVO", "📦 OPERACIÓN & FUNNEL", "👥 PRODUCTIVIDAD", "📈 CONVERSIÓN", "💰 RENTABILIDAD", "⚠️ ALERTAS"])

    # --- TAB 1: RESUMEN EJECUTIVO ---
    with tabs[0]:
        c1, c2, c3, c4 = st.columns(4)
        ing_t = df_f['Total_Ing'].sum()
        with c1: st.markdown(f'<div class="exec-card"><p class="exec-label">Total Ingresos</p><p class="exec-value">{ing_t:,.0f}</p></div>', unsafe_allow_html=True)
        
        conv_g = 0
        if not df_mf.empty:
            rec_pzas = df_mf.apply(lambda r: min(r['Dev'], r['Venta']), axis=1).sum()
            conv_g = safe_div(rec_pzas, df_mf['Dev'].sum()) * 100
        with c2: st.markdown(f'<div class="exec-card"><p class="exec-label">Conversión Gral.</p><p class="exec-value">{conv_g:.1f}%</p></div>', unsafe_allow_html=True)
        
        val_rec = df_mf.apply(lambda r: r['Neta_$'] * safe_div(min(r['Dev'], r['Venta']), r['Venta']), axis=1).sum() if not df_mf.empty else 0
        with c3: st.markdown(f'<div class="exec-card"><p class="exec-label">Recuperación $</p><p class="exec-value">${val_rec/1e6:.1f}M</p></div>', unsafe_allow_html=True)
        
        mejor_t = df_f.groupby('Tienda')['Total_Ing'].sum().idxmax() if not df_f.empty else "N/A"
        with c4: st.markdown(f'<div class="exec-card"><p class="exec-label">Mejor Tienda</p><p class="exec-value" style="font-size:20px">{mejor_t}</p></div>', unsafe_allow_html=True)

        st.markdown('<p class="section-title">Evolución Semanal de Recuperación</p>', unsafe_allow_html=True)
        wow = df_op.groupby('Semana')['Total_Ing'].sum().reset_index()
        st.plotly_chart(px.area(wow, x='Semana', y='Total_Ing', title="Tendencia de Ingresos WoW", color_discrete_sequence=['#1F497D']), use_container_width=True)

    # --- TAB 2: OPERACIÓN & FUNNEL ---
    with tabs[1]:
        st.markdown('<p class="section-title">Funnel de Eficiencia Operativa</p>', unsafe_allow_html=True)
        f_ing, f_hab, f_ubi = df_f['Total_Ing'].sum(), df_f['Pzas_Hab'].sum(), df_f['Pzas_Ubi'].sum()
        fig_f = go.Figure(go.Funnel(
            y = ["Ingreso", "Habilitado", "Ubicado"],
            x = [f_ing, f_hab, f_ubi],
            textinfo = "value+percent initial",
            marker = {"color": ["#1F497D", "#16355C", "#E6007E"]}
        ))
        st.plotly_chart(fig_f, use_container_width=True)
        
        st.markdown('<p class="section-title">Desempeño por Tienda</p>', unsafe_allow_html=True)
        st.dataframe(df_f.groupby('Tienda').agg({'Total_Ing': 'sum', 'Pzas_Hab': 'sum', 'Pzas_Ubi': 'sum', 'Real_Rec': 'sum'}).sort_values('Total_Ing', ascending=False), use_container_width=True)

    # --- TAB 3: PRODUCTIVIDAD ---
    with tabs[2]:
        st.markdown('<p class="section-title">Ranking de Productividad (Usuarios)</p>', unsafe_allow_html=True)
        u_rank = df_cf.groupby(['Nombre', 'Tienda'])['Pzas'].sum().reset_index().sort_values('Pzas', ascending=False)
        c_t, c_b = st.columns(2)
        with c_t: 
            st.subheader("Top 10 Colaboradores")
            st.dataframe(u_rank.head(10), use_container_width=True)
        with c_b:
            st.subheader("Bottom 10 Colaboradores")
            st.dataframe(u_rank.tail(10), use_container_width=True)
        
        st.plotly_chart(px.pie(u_rank.head(20), values='Pzas', names='Nombre', title="Participación % Top 20"), use_container_width=True)

    # --- TAB 4: CONVERSIÓN ---
    with tabs[3]:
        st.markdown('<p class="section-title">Análisis Estratégico de Conversión</p>', unsafe_allow_html=True)
        if not df_mf.empty:
            t_conv = df_mf.groupby('Tienda').apply(lambda x: safe_div(x.apply(lambda r: min(r['Dev'], r['Venta']), axis=1).sum(), x['Dev'].sum())*100).reset_index(name='Conv_%')
            st.plotly_chart(px.bar(t_conv.sort_values('Conv_%', ascending=False), x='Tienda', y='Conv_%', color='Conv_%', color_continuous_scale='RdYlGn'), use_container_width=True)
            
            st.markdown("### Heatmap de Conversión por Tienda y Semana")
            h_map = df_models.groupby(['Tienda', 'Semana']).apply(lambda x: safe_div(x.apply(lambda r: min(r['Dev'], r['Venta']), axis=1).sum(), x['Dev'].sum())*100).unstack().fillna(0)
            st.plotly_chart(px.imshow(h_map, color_continuous_scale='RdYlGn', title="Matriz de Eficiencia"), use_container_width=True)

    # --- TAB 5: RENTABILIDAD ---
    with tabs[4]:
        st.markdown('<p class="section-title">Recuperación Económica Nacional</p>', unsafe_allow_html=True)
        if not df_mf.empty:
            df_mf['Rec_Val'] = df_mf.apply(lambda r: r['Neta_$'] * safe_div(min(r['Dev'], r['Venta']), r['Venta']), axis=1)
            r_stats = df_mf.groupby('Tienda').agg({'Neta_$': 'sum', 'Rec_Val': 'sum'}).reset_index()
            r_stats['Pendiente'] = r_stats['Neta_$'] - r_stats['Rec_Val']
            
            fig_r = go.Figure()
            fig_r.add_trace(go.Bar(name='Recuperado', x=r_stats['Tienda'], y=r_stats['Rec_Val'], marker_color='#28a745'))
            fig_r.add_trace(go.Bar(name='Pendiente', x=r_stats['Tienda'], y=r_stats['Pendiente'], marker_color='#dc3545'))
            fig_r.update_layout(barmode='stack', title="Balance de Recuperación $ por Tienda")
            st.plotly_chart(fig_r, use_container_width=True)

    # --- TAB 6: ALERTAS ---
    with tabs[5]:
        st.markdown('<p class="section-title">Alertas Inteligentes de Negocio</p>', unsafe_allow_html=True)
        # Alerta de Conversión
        if conv_g < 80:
            st.markdown(f'<div class="alert-card alert-high">⚠️ <b>BAJA CONVERSIÓN NACIONAL:</b> La conversión actual ({conv_g:.1f}%) está por debajo de la meta del 80%.</div>', unsafe_allow_html=True)
        
        # Alerta WoW
        if len(wow) > 1:
            last = wow.iloc[-1]['Total_Ing']
            prev = wow.iloc[-2]['Total_Ing']
            drop = (last - prev) / prev
            if drop < -0.20:
                st.markdown(f'<div class="alert-card alert-high">🚨 <b>CAÍDA CRÍTICA WoW:</b> Los ingresos han caído un {abs(drop)*100:.1f}% respecto a la semana anterior.</div>', unsafe_allow_html=True)
        
        # Usuarios sin actividad
        st.info("💡 Sugerencia: Revisa el ranking de productividad para identificar a los 10 colaboradores con menor desempeño.")

else:
    st.info("Iniciando plataforma... Conectando con los servicios de datos de Price Shoes.")
