import streamlit as st

import pandas as pd

import plotly.graph_objects as go

import requests

from io import BytesIO



# =========================================================================

# --- CONFIGURACIÓN EJECUTIVA Y ESTILOS ---

# =========================================================================

st.set_page_config(page_title="Price Shoes - Inteligencia Operativa", layout="wide", page_icon="📈")



# Estilos de Reporte Ejecutivo (Price Shoes Identity)

st.markdown("""

    <style>

    /* Estilo General */

    .main { background-color: #FFFFFF; }

    .main-title { color: #000000; font-size: 38px; font-weight: 900; margin-bottom: 0px; letter-spacing: -1px; }

    .sub-title { color: #E6007E; font-size: 14px; font-weight: 800; margin-top: -5px; text-transform: uppercase; letter-spacing: 2px; }

    .section-header { color: #1F497D; font-weight: 800; font-size: 20px; margin-top: 30px; margin-bottom: 15px; border-left: 6px solid #E6007E; padding-left: 12px; }

    

    /* Tarjetas Ejecutivas */

    .exec-card { background-color: #FDFDFD; border: 1px solid #EAEAEA; border-radius: 8px; padding: 20px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }

    .exec-label { color: #666666; font-size: 12px; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }

    .exec-value { color: #1F497D; font-size: 28px; font-weight: 900; margin-bottom: 5px; }

    .exec-delta { font-size: 14px; font-weight: 700; }

    .delta-pos { color: #28A745; }

    .delta-neg { color: #DC3545; }

    

    /* Bloqueo de Gráficos (Estabilidad Web) */

    .stPlotlyChart { pointer-events: none; } /* Bloquea zoom/scroll accidental */

    

    /* Pestañas Personalizadas */

    .stTabs [data-baseweb="tab-list"] { gap: 24px; }

    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #F8F9FA; border-radius: 4px 4px 0 0; padding: 10px 20px; font-weight: 700; color: #1F497D; }

    .stTabs [aria-selected="true"] { background-color: #1F497D !important; color: white !important; }

    </style>

    """, unsafe_allow_html=True)



# =========================================================================

# --- MOTOR DE DATOS INTELIGENTE ---

# =========================================================================

@st.cache_data(ttl=600)

def load_business_data():

    URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSV6dtosg0Ydt0o3NMFezC--NjHfEW82onFeY2JR4PTYD3ylG4ZlRaQBquscFrCy_Lysrau9zTW6dkn/pub?output=xlsx"

    try:

        response = requests.get(URL, timeout=30)

        xls = pd.ExcelFile(BytesIO(response.content), engine='openpyxl')

        data_rows = []

        tiendas_objetivo = ['Vallejo', 'Arco Norte', 'Puebla Sur', 'Miravalle', 'Ecatepec']

        meses_dict = {'enero':'Enero', 'febrero':'Febrero', 'marzo':'Marzo', 'abril':'Abril', 'mayo':'Mayo', 'junio':'Junio', 'julio':'Julio', 'agosto':'Agosto', 'septiembre':'Septiembre', 'octubre':'Octubre', 'noviembre':'Noviembre', 'diciembre':'Diciembre'}



        for sheet_name in xls.sheet_names:

            if not sheet_name.lower().strip().startswith('sem'): continue

            df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None, engine='openpyxl')

            curr_date = "Sin Fecha"

            for i, row in df_raw.iterrows():

                if len(row) < 2: continue

                val = str(row[1]).strip()

                if '2026' in val and ',' in val: curr_date = val; continue

                if any(t.lower() in val.lower() for t in tiendas_objetivo) and len(val) < 30:

                    try:

                        mes_ext = "Otros"

                        for k, v in meses_dict.items():

                            if k in curr_date.lower(): mes_ext = v; break

                        data_rows.append({

                            'Mes': mes_ext, 'Semana': sheet_name.strip(), 'Tienda': val,

                            'Ing_Sis': row[2], 'Ing_Muertos': row[4], 'Ing_Cajas': row[5],

                            'Meta_Rec': row[7], 'Real_Rec': row[8], 'Pzas_Rec': row[9],

                            'Pzas_Hab': row[10], 'Pzas_Ubi': row[11]

                        })

                    except: continue

        df = pd.DataFrame(data_rows)

        for col in ['Ing_Sis', 'Ing_Muertos', 'Ing_Cajas', 'Meta_Rec', 'Real_Rec', 'Pzas_Rec', 'Pzas_Hab', 'Pzas_Ubi']:

            df[col] = df[col].apply(lambda x: float(str(x).replace(',', '').replace('%', '').strip()) if pd.notna(x) else 0.0)

        df['Total_Ingresos'] = df['Ing_Sis'] + df['Ing_Muertos'] + df['Ing_Cajas']

        return df

    except: return pd.DataFrame()



df = load_business_data()



# --- HEADER EJECUTIVO ---

col_logo, col_text = st.columns([1, 6])

with col_text:

    st.markdown('<p class="main-title">PRICE SHOES • Business Intelligence</p>', unsafe_allow_html=True)

    st.markdown('<p class="sub-title">CONTROL OPERATIVO DE RECUPERACIÓN (CAMBIOS Y MUERTOS)</p>', unsafe_allow_html=True)



if not df.empty:

    # --- FILTROS GLOBALES (SIDEBAR) ---

    st.sidebar.image("https://priceshoes.com/media/logo/stores/1/logo_price_shoes.png", width=150)

    st.sidebar.markdown("### 🎛️ Filtros de Control")

    

    meses_orden = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

    meses_presentes = sorted(df['Mes'].unique().tolist(), key=lambda x: meses_orden.index(x) if x in meses_orden else 99)

    sel_mes = st.sidebar.selectbox("Periodo Mensual:", ["Anual"] + meses_presentes)

    

    df_mes = df if sel_mes == "Anual" else df[df['Mes'] == sel_mes]

    semanas = ["Todas las Semanas"] + sorted(df_mes['Semana'].unique().tolist(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))

    sel_sem = st.sidebar.selectbox("Corte Semanal:", semanas)

    

    tiendas = ["Consolidado Total"] + sorted(df['Tienda'].unique().tolist())

    sel_tienda = st.sidebar.selectbox("Unidad de Negocio:", tiendas)



    # Filtrado Final

    df_f = df_mes.copy()

    if sel_sem != "Todas las Semanas": df_f = df_f[df_f['Semana'] == sel_sem]

    if sel_tienda != "Consolidado Total": df_f = df_f[df_f['Tienda'] == sel_tienda]



    # --- NAVEGACIÓN POR PESTAÑAS ---

    tab1, tab2, tab3 = st.tabs(["📊 RESUMEN EJECUTIVO", "🚀 PRODUCTIVIDAD Y RENDIMIENTO", "📑 AUDITORÍA DE DATOS"])



    # =========================================================================

    # TAB 1: RESUMEN EJECUTIVO

    # =========================================================================

    with tab1:

        st.markdown('<p class="section-header">Indicadores Clave de Desempeño (KPIs)</p>', unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)

        ing = df_f['Total_Ingresos'].sum()

        hab = df_f['Pzas_Hab'].sum()

        ubi = df_f['Pzas_Ubi'].sum()

        eff_rec = (df_f['Real_Rec'].sum() / df_f['Meta_Rec'].sum() * 100) if df_f['Meta_Rec'].sum() > 0 else 0

        

        with c1: st.markdown(f'<div class="exec-card"><p class="exec-label">📥 Ingreso Total</p><p class="exec-value">{ing:,.0f}</p><p class="exec-delta">Piezas Recuperadas</p></div>', unsafe_allow_html=True)

        with c2: st.markdown(f'<div class="exec-card"><p class="exec-label">✨ Tasa Habilitado</p><p class="exec-value">{(hab/ing*100 if ing>0 else 0):.1f}%</p><p class="exec-delta">{hab:,.0f} Pzas Listas</p></div>', unsafe_allow_html=True)

        with c3: st.markdown(f'<div class="exec-card"><p class="exec-label">📍 Tasa Ubicación</p><p class="exec-value">{(ubi/ing*100 if ing>0 else 0):.1f}%</p><p class="exec-delta">{ubi:,.0f} en Piso</p></div>', unsafe_allow_html=True)

        with c4: st.markdown(f'<div class="exec-card"><p class="exec-label">🎯 Efic. Recorridos</p><p class="exec-value">{eff_rec:.1f}%</p><p class="exec-delta">Cumplimiento Meta</p></div>', unsafe_allow_html=True)



        col_g1, col_g2 = st.columns(2)

        with col_g1:

            st.markdown('<p class="section-header">Distribución de Ingresos por Tienda</p>', unsafe_allow_html=True)

            df_pie = df_f.groupby('Tienda')['Total_Ingresos'].sum().reset_index()

            fig_pie = go.Figure(data=[go.Pie(labels=df_pie['Tienda'], values=df_pie['Total_Ingresos'], hole=.4, marker_colors=['#1F497D', '#E6007E', '#D9D9D9', '#555555', '#A6A6A6'])])

            fig_pie.update_layout(showlegend=True, height=400, margin=dict(t=0, b=0, l=0, r=0))

            st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False, 'staticPlot': True})

            

        with col_g2:

            st.markdown('<p class="section-header">Balance Operativo: Ingreso vs Salida a Piso</p>', unsafe_allow_html=True)

            df_bar = df_f.groupby('Tienda').agg({'Total_Ingresos':'sum', 'Pzas_Ubi':'sum'}).reset_index().sort_values('Total_Ingresos', ascending=False)

            fig_bar = go.Figure()

            fig_bar.add_trace(go.Bar(x=df_bar['Tienda'], y=df_bar['Total_Ingresos'], name="Ingreso", marker_color='#1F497D'))

            fig_bar.add_trace(go.Bar(x=df_bar['Tienda'], y=df_bar['Pzas_Ubi'], name="Ubicado", marker_color='#E6007E'))

            fig_bar.update_layout(barmode='group', plot_bgcolor='white', height=400, margin=dict(t=0, b=0))

            st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False, 'staticPlot': True})



    # =========================================================================

    # TAB 2: PRODUCTIVIDAD

    # =========================================================================

    with tab2:

        st.markdown('<p class="section-header">Métricas de Productividad por Unidad</p>', unsafe_allow_html=True)

        df_prod = df_f.groupby('Tienda').agg({

            'Total_Ingresos': 'sum', 'Pzas_Rec': 'sum', 'Real_Rec': 'sum', 'Pzas_Hab': 'sum'

        }).reset_index()

        

        df_prod['Pzas x Recorrido'] = (df_prod['Pzas_Rec'] / df_prod['Real_Rec']).fillna(0)

        df_prod['Productividad Habilitado'] = (df_prod['Pzas_Hab'] / df_prod['Total_Ingresos'] * 100).fillna(0)

        

        c_p1, c_p2 = st.columns(2)

        with c_p1:

            st.markdown('<p class="graph-title">Densidad de Recolección (Piezas por Recorrido)</p>', unsafe_allow_html=True)

            fig_p1 = go.Figure(go.Bar(x=df_prod['Tienda'], y=df_prod['Pzas x Recorrido'], marker_color='#1F497D', text=df_prod['Pzas x Recorrido'].round(1), textposition='auto'))

            fig_p1.update_layout(plot_bgcolor='white', height=400)

            st.plotly_chart(fig_p1, use_container_width=True, config={'staticPlot': True})

            

        with c_p2:

            st.markdown('<p class="graph-title">Evolución de Productividad Semanal</p>', unsafe_allow_html=True)

            df_ev = df_f.groupby('Semana').agg({'Total_Ingresos':'sum', 'Pzas_Hab':'sum'}).reset_index()

            df_ev['n'] = df_ev['Semana'].apply(lambda x: int(''.join(filter(str.isdigit, x)) or 0))

            df_ev = df_ev.sort_values('n')

            fig_ev = go.Figure()

            fig_ev.add_trace(go.Scatter(x=df_ev['Semana'], y=df_ev['Total_Ingresos'], name="Ingresos", line=dict(color='#1F497D', width=4)))

            fig_ev.add_trace(go.Scatter(x=df_ev['Semana'], y=df_ev['Pzas_Hab'], name="Habilitado", line=dict(color='#E6007E', width=4)))

            fig_ev.update_layout(plot_bgcolor='white', height=400)

            st.plotly_chart(fig_ev, use_container_width=True, config={'staticPlot': True})



    # =========================================================================

    # TAB 3: AUDITORÍA

    # =========================================================================

    with tab3:

        st.markdown('<p class="section-header">Matriz Consolidada de Auditoría</p>', unsafe_allow_html=True)

        df_audit = df_f.groupby(['Semana', 'Tienda']).agg({

            'Ing_Sis': 'sum', 'Ing_Muertos': 'sum', 'Ing_Cajas': 'sum', 'Total_Ingresos': 'sum',

            'Pzas_Rec': 'sum', 'Pzas_Hab': 'sum', 'Pzas_Ubi': 'sum', 'Real_Rec': 'sum'

        }).reset_index()

        

        # Formateo de porcentajes

        df_audit['% Hab'] = (df_audit['Pzas_Hab'] / df_audit['Total_Ingresos'] * 100).fillna(0).round(1).astype(str) + '%'

        df_audit['% Ubi'] = (df_audit['Pzas_Ubi'] / df_audit['Total_Ingresos'] * 100).fillna(0).round(1).astype(str) + '%'

        

        st.dataframe(df_audit.sort_values(['Semana', 'Total_Ingresos'], ascending=[True, False]), use_container_width=True)

        

        st.download_button(label="📥 Descargar Reporte en CSV", data=df_audit.to_csv(index=False).encode('utf-8'), file_name='reporte_operativo_price.csv', mime='text/csv')



else:

    st.info("📊 El sistema está listo. Por favor, asegúrate de que el Google Sheet esté publicado correctamente.")
