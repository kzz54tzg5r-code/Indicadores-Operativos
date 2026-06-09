import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from io import BytesIO

# =========================================================================
# --- CONFIGURACIÓN EJECUTIVA Y ESTILOS ---
# =========================================================================
st.set_page_config(page_title="Price Shoes - Intelligence WoW", layout="wide", page_icon="👚")

st.markdown("""
    <style>
    .main-title { color: #000000; font-size: 34px; font-weight: 900; margin-bottom: 0px; }
    .sub-title { color: #E6007E; font-size: 14px; font-weight: 800; margin-top: -5px; text-transform: uppercase; }
    .section-header { color: #1F497D; font-weight: 800; font-size: 18px; margin-top: 25px; margin-bottom: 10px; border-left: 5px solid #E6007E; padding-left: 10px; }
    
    /* Tarjetas WoW (Semana vs Semana) */
    .wow-card-header { background-color: #1F497D; color: white; text-align: center; padding: 6px; border-radius: 6px 6px 0 0; font-weight: bold; font-size: 13px; }
    .wow-card-body { background-color: #F8F9FA; border: 1px solid #E0E0E0; border-top: none; border-radius: 0 0 6px 6px; padding: 12px; margin-bottom: 15px; }
    .wow-metric-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; border-bottom: 1px solid #EEE; padding-bottom: 4px; }
    .wow-label { color: #666; font-size: 10px; font-weight: 700; text-transform: uppercase; }
    .wow-value { color: #1F497D; font-size: 15px; font-weight: 800; }
    .wow-trend { font-size: 12px; font-weight: 800; }
    .trend-up { color: #28A745; }
    .trend-down { color: #DC3545; }
    .trend-neutral { color: #6C757D; }
    
    /* Bloqueo de Gráficos */
    .stPlotlyChart { pointer-events: none; }
    </style>
    """, unsafe_allow_html=True)

# =========================================================================
# --- MOTOR DE DATOS ---
# =========================================================================
@st.cache_data(ttl=600)
def load_data():
    URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSV6dtosg0Ydt0o3NMFezC--NjHfEW82onFeY2JR4PTYD3ylG4ZlRaQBquscFrCy_Lysrau9zTW6dkn/pub?output=xlsx"
    try:
        response = requests.get(URL, timeout=30)
        xls = pd.ExcelFile(BytesIO(response.content), engine='openpyxl')
        data_rows = []
        tiendas = ['Vallejo', 'Arco Norte', 'Puebla Sur', 'Miravalle', 'Ecatepec']
        meses_m = {'enero':'Enero', 'febrero':'Febrero', 'marzo':'Marzo', 'abril':'Abril', 'mayo':'Mayo', 'junio':'Junio', 'julio':'Julio', 'agosto':'Agosto', 'septiembre':'Septiembre', 'octubre':'Octubre', 'noviembre':'Noviembre', 'diciembre':'Diciembre'}

        for sheet in xls.sheet_names:
            if not sheet.lower().startswith('sem'): continue
            df_s = pd.read_excel(xls, sheet_name=sheet, header=None, engine='openpyxl')
            dt = "Sin Fecha"
            for i, r in df_s.iterrows():
                if len(r) < 2: continue
                v = str(r[1]).strip()
                if '2026' in v and ',' in v: dt = v; continue
                if any(t.lower() in v.lower() for t in tiendas) and len(v) < 30:
                    try:
                        m_ext = "Otros"
                        for k, val in meses_m.items():
                            if k in dt.lower(): m_ext = val; break
                        data_rows.append({
                            'Mes': m_ext, 'Semana': sheet.strip(), 'Tienda': v,
                            'Ing_Sis': r[2], 'Ing_Muertos': r[4], 'Ing_Cajas': r[5],
                            'Meta_Rec': r[7], 'Real_Rec': r[8], 'Pzas_Rec': r[9],
                            'Pzas_Hab': r[10], 'Pzas_Ubi': r[11]
                        })
                    except: continue
        df = pd.DataFrame(data_rows)
        for c in ['Ing_Sis', 'Ing_Muertos', 'Ing_Cajas', 'Meta_Rec', 'Real_Rec', 'Pzas_Rec', 'Pzas_Hab', 'Pzas_Ubi']:
            df[c] = df[c].apply(lambda x: float(str(x).replace(',', '').replace('%', '').strip()) if pd.notna(x) else 0.0)
        df['Total_Ingresos'] = df['Ing_Sis'] + df['Ing_Muertos'] + df['Ing_Cajas']
        return df
    except: return pd.DataFrame()

df = load_data()

# --- HEADER ---
st.markdown('<p class="main-title">PRICE SHOES • Business Intelligence</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">ANÁLISIS COMPARATIVO SEMANA CONTRA SEMANA (WoW)</p>', unsafe_allow_html=True)

if not df.empty:
    # --- SIDEBAR ---
    st.sidebar.markdown("### 🔍 Filtros Generales")
    sel_tienda = st.sidebar.selectbox("Unidad de Negocio:", ["Consolidado"] + sorted(df['Tienda'].unique().tolist()))
    
    df_f = df.copy()
    if sel_tienda != "Consolidado": df_f = df_f[df_f['Tienda'] == sel_tienda]

    # --- TARJETAS WoW (ÚLTIMAS 4 SEMANAS) ---
    st.markdown('<p class="section-header">📊 Resumen Operativo WoW (Últimas 4 Semanas)</p>', unsafe_allow_html=True)
    
    weeks = sorted(df['Semana'].unique().tolist(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    last_4 = weeks[-4:]
    
    cols = st.columns(4)
    for i, sem in enumerate(last_4):
        # Datos Semana Actual
        df_curr = df_f[df_f['Semana'] == sem]
        ing = df_curr['Total_Ingresos'].sum()
        hab = df_curr['Pzas_Hab'].sum()
        ubi = df_curr['Pzas_Ubi'].sum()
        rec = (df_curr['Real_Rec'].sum() / df_curr['Meta_Rec'].sum() * 100) if df_curr['Meta_Rec'].sum() > 0 else 0
        
        # Datos Semana Anterior (para flechas)
        idx = weeks.index(sem)
        if idx > 0:
            sem_prev = weeks[idx-1]
            df_prev = df_f[df_f['Semana'] == sem_prev]
            ing_p = df_prev['Total_Ingresos'].sum()
            hab_p = df_prev['Pzas_Hab'].sum()
            ubi_p = df_prev['Pzas_Ubi'].sum()
            rec_p = (df_prev['Real_Rec'].sum() / df_prev['Meta_Rec'].sum() * 100) if df_prev['Meta_Rec'].sum() > 0 else 0
            
            def get_trend(curr, prev):
                if prev == 0: return "—", "trend-neutral"
                diff = ((curr - prev) / prev) * 100
                if diff > 0.5: return f"▲ {diff:.1f}%", "trend-up"
                if diff < -0.5: return f"▼ {abs(diff):.1f}%", "trend-down"
                return "● 0%", "trend-neutral"
            
            t_ing, c_ing = get_trend(ing, ing_p)
            t_hab, c_hab = get_trend(hab, hab_p)
            t_ubi, c_ubi = get_trend(ubi, ubi_p)
            t_rec, c_rec = get_trend(rec, rec_p)
        else:
            t_ing, t_hab, t_ubi, t_rec = "—", "—", "—", "—"
            c_ing = c_hab = c_ubi = c_rec = "trend-neutral"

        with cols[i]:
            st.markdown(f'<div class="wow-card-header">{sem}</div>', unsafe_allow_html=True)
            st.markdown(f"""
                <div class="wow-card-body">
                    <div class="wow-metric-row"><span class="wow-label">Ingresos</span><span class="wow-value">{ing:,.0f}</span><span class="wow-trend {c_ing}">{t_ing}</span></div>
                    <div class="wow-metric-row"><span class="wow-label">Habilitado</span><span class="wow-value">{hab:,.0f}</span><span class="wow-trend {c_hab}">{t_hab}</span></div>
                    <div class="wow-metric-row"><span class="wow-label">Ubicado</span><span class="wow-value">{ubi:,.0f}</span><span class="wow-trend {c_ubi}">{t_ubi}</span></div>
                    <div class="wow-metric-row"><span class="wow-label">% Recorridos</span><span class="wow-value">{rec:.1f}%</span><span class="wow-trend {c_rec}">{t_rec}</span></div>
                </div>
            """, unsafe_allow_html=True)

    # --- PESTAÑAS DE ANÁLISIS ---
    tab1, tab2 = st.tabs(["📈 ANÁLISIS DE TENDENCIAS", "🔍 DETALLE POR SUCURSAL"])
    
    with tab1:
        c_g1, c_g2 = st.columns(2)
        with c_g1:
            st.markdown('<p class="section-header">Mezcla de Ingresos (Fuentes)</p>', unsafe_allow_html=True)
            df_m = df_f.groupby('Semana').agg({'Ing_Sis':'sum', 'Ing_Muertos':'sum', 'Ing_Cajas':'sum'}).reset_index()
            df_m['n'] = df_m['Semana'].apply(lambda x: int(''.join(filter(str.isdigit, x)) or 0))
            df_m = df_m.sort_values('n')
            fig1 = go.Figure()
            fig1.add_trace(go.Bar(x=df_m['Semana'], y=df_m['Ing_Sis'], name="Sistema", marker_color='#1F497D'))
            fig1.add_trace(go.Bar(x=df_m['Semana'], y=df_m['Ing_Muertos'], name="Muertos", marker_color='#E6007E'))
            fig1.add_trace(go.Bar(x=df_m['Semana'], y=df_m['Ing_Cajas'], name="Cajas", marker_color='#A6A6A6'))
            fig1.update_layout(barmode='stack', height=350, plot_bgcolor='white', margin=dict(t=0, b=0))
            st.plotly_chart(fig1, use_container_width=True, config={'staticPlot': True})
            
        with c_g2:
            st.markdown('<p class="section-header">Eficiencia: Habilitado vs Ubicado</p>', unsafe_allow_html=True)
            df_e = df_f.groupby('Semana').agg({'Pzas_Hab':'sum', 'Pzas_Ubi':'sum'}).reset_index()
            df_e['n'] = df_e['Semana'].apply(lambda x: int(''.join(filter(str.isdigit, x)) or 0))
            df_e = df_e.sort_values('n')
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=df_e['Semana'], y=df_e['Pzas_Hab'], name="Habilitado", line=dict(color='#E6007E', width=3)))
            fig2.add_trace(go.Scatter(x=df_e['Semana'], y=df_e['Pzas_Ubi'], name="Ubicado", line=dict(color='#1F497D', width=3), fill='tonexty'))
            fig2.update_layout(height=350, plot_bgcolor='white', margin=dict(t=0, b=0))
            st.plotly_chart(fig2, use_container_width=True, config={'staticPlot': True})

    with tab2:
        st.markdown('<p class="section-header">Rendimiento Operativo por Tienda</p>', unsafe_allow_html=True)
        df_t = df_f.groupby('Tienda').agg({'Total_Ingresos':'sum', 'Pzas_Hab':'sum', 'Pzas_Ubi':'sum', 'Real_Rec':'sum', 'Meta_Rec':'sum'}).reset_index()
        df_t['% Recorridos'] = (df_t['Real_Rec'] / df_t['Meta_Rec'] * 100).fillna(0).round(1)
        
        c_t1, c_t2 = st.columns([2, 1])
        with c_t1:
            fig_t = go.Figure()
            fig_t.add_trace(go.Bar(x=df_t['Tienda'], y=df_t['Total_Ingresos'], name="Ingresos", marker_color='#1F497D'))
            fig_t.add_trace(go.Bar(x=df_t['Tienda'], y=df_t['Pzas_Hab'], name="Habilitado", marker_color='#E6007E'))
            fig_t.update_layout(barmode='group', height=400, plot_bgcolor='white')
            st.plotly_chart(fig_t, use_container_width=True, config={'staticPlot': True})
        with c_t2:
            st.dataframe(df_t[['Tienda', 'Total_Ingresos', '% Recorridos']].sort_values('Total_Ingresos', ascending=False), use_container_width=True)

else:
    st.info("📊 El dashboard está listo. Asegúrate de publicar el Google Sheet como Excel (.xlsx) y seleccionar 'Todo el documento'.")
