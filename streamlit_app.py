import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from io import BytesIO

# =========================================================================
# --- CONFIGURACIÓN DE INTERFAZ Y ESTILOS ---
# =========================================================================
st.set_page_config(page_title="Price Shoes - Operaciones Ropa", layout="wide", page_icon="👚")

st.markdown("""
    <style>
    .main-title { color: #000000; font-size: 34px; font-weight: 800; margin-bottom: 0px; }
    .sub-title { color: #E6007E; font-size: 15px; font-weight: bold; margin-top: -5px; text-transform: uppercase; }
    .graph-title { color: #1F497D; font-weight: bold; font-size: 18px; margin-top: 35px; margin-bottom: 15px; border-left: 5px solid #1F497D; padding-left: 10px; }
    
    /* Estilos para las tarjetas de resumen macro */
    .macro-card-header { background-color: #1F497D; color: white; text-align: center; padding: 8px; border-radius: 4px 4px 0 0; font-weight: bold; font-size: 14px; margin-bottom: 0; }
    .macro-card-body { background-color: #F8F9FA; border: 1px solid #D9D9D9; border-top: none; border-radius: 0 0 4px 4px; padding: 12px; text-align: center; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .macro-label { color: #555555; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-bottom: 2px; }
    .macro-value { color: #1F497D; font-size: 18px; font-weight: bold; margin-bottom: 0; }
    .macro-pct { color: #E6007E; font-size: 14px; font-weight: bold; }
    .macro-divider { border-top: 1px dashed #D9D9D9; margin: 8px 0; }
    </style>
    """, unsafe_allow_html=True)

# =========================================================================
# --- MOTOR DE CARGA MULTI-PESTAÑA (EXCEL) ---
# =========================================================================
@st.cache_data(ttl=600)
def load_all_data():
    URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSV6dtosg0Ydt0o3NMFezC--NjHfEW82onFeY2JR4PTYD3ylG4ZlRaQBquscFrCy_Lysrau9zTW6dkn/pub?output=xlsx"
    
    try:
        response = requests.get(URL, timeout=30)
        response.raise_for_status()
        xls = pd.ExcelFile(BytesIO(response.content), engine='openpyxl')
        
        data_rows = []
        tiendas_objetivo = ['Vallejo', 'Arco Norte', 'Puebla Sur', 'Miravalle', 'Ecatepec']
        
        # Diccionario para mapear meses dinámicamente
        meses_dict = {
            'enero': 'Enero', 'febrero': 'Febrero', 'marzo': 'Marzo', 'abril': 'Abril',
            'mayo': 'Mayo', 'junio': 'Junio', 'julio': 'Julio', 'agosto': 'Agosto',
            'septiembre': 'Septiembre', 'octubre': 'Octubre', 'noviembre': 'Noviembre', 'diciembre': 'Diciembre'
        }

        for sheet_name in xls.sheet_names:
            if not sheet_name.lower().strip().startswith('sem'): continue
            df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None, engine='openpyxl')
            current_date = "Sin Fecha"
            
            for i, row in df_raw.iterrows():
                if len(row) < 2: continue
                val = str(row[1]).strip()
                if '2026' in val and ',' in val:
                    current_date = val
                    continue
                if any(t.lower() in val.lower() for t in tiendas_objetivo) and len(val) < 30:
                    try:
                        # Extraer mes real de la cadena de fecha
                        mes_encontrado = "Otros"
                        for key, name in meses_dict.items():
                            if key in current_date.lower():
                                mes_encontrado = name
                                break
                                
                        data_rows.append({
                            'Mes': mes_encontrado,
                            'Semana': sheet_name.strip(),
                            'Tienda': val,
                            'Sis_Aduana': row[2], 'Muertos': row[4], 'Cajas': row[5],
                            'Meta_Rec': row[7], 'Real_Rec': row[8],
                            'Habilitadas': row[10], 'Ubicadas': row[11]
                        })
                    except Exception: continue

        if not data_rows: return pd.DataFrame()
        df = pd.DataFrame(data_rows)
        def clean_num(x):
            try: return float(str(x).replace(',', '').replace('%', '').strip())
            except: return 0.0
        for col in ['Sis_Aduana', 'Muertos', 'Cajas', 'Meta_Rec', 'Real_Rec', 'Habilitadas', 'Ubicadas']:
            df[col] = df[col].apply(clean_num)
        df['Total_Ingresos'] = df['Sis_Aduana'] + df['Muertos'] + df['Cajas']
        return df
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return pd.DataFrame()

# =========================================================================
# --- LÓGICA DE INTERFAZ ---
# =========================================================================
df = load_all_data()

st.markdown('<p class="main-title">👚 PRICE SHOES • Operaciones Ropa</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">DASHBOARD ANUAL DINÁMICO</p>', unsafe_allow_html=True)

if not df.empty:
    # --- FILTROS DE REPORTE (SIDEBAR) ---
    st.sidebar.markdown("### 🔍 Filtros de Reporte")
    
    # Orden cronológico de meses
    meses_orden = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    meses_presentes = sorted(df['Mes'].unique().tolist(), key=lambda x: meses_orden.index(x) if x in meses_orden else 99)
    sel_mes = st.sidebar.selectbox("Mes:", ["Todos"] + meses_presentes)
    
    # Filtrar por mes para actualizar semanas
    df_mes = df if sel_mes == "Todos" else df[df['Mes'] == sel_mes]
    
    # Filtro Semana
    semanas_presentes = sorted(df_mes['Semana'].unique().tolist(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    sel_sem = st.sidebar.selectbox("Semana:", ["Todas"] + semanas_presentes)
    
    # Filtro Tienda
    tiendas_presentes = sorted(df['Tienda'].unique().tolist())
    sel_tienda = st.sidebar.selectbox("Tienda:", ["Todas"] + tiendas_presentes)

    # Aplicar filtros al DataFrame principal para las tarjetas
    df_filtered = df_mes.copy()
    if sel_sem != "Todas": df_filtered = df_filtered[df_filtered['Semana'] == sel_sem]
    if sel_tienda != "Todas": df_filtered = df_filtered[df_filtered['Tienda'] == sel_tienda]

    # --- RESUMEN MACRO DINÁMICO (ÚLTIMAS 4 SEMANAS DEL FILTRO) ---
    st.markdown('<p class="graph-title">📊 Resumen Macro de Operación (Dinámico)</p>', unsafe_allow_html=True)
    
    # Obtener las semanas según el filtro actual
    semanas_filtro = sorted(df_filtered['Semana'].unique().tolist(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    
    # Si hay muchas semanas, mostramos las últimas 4 del filtro. Si hay pocas, mostramos las que haya.
    semanas_a_mostrar = semanas_filtro[-4:] if len(semanas_filtro) > 4 else semanas_filtro
    
    if semanas_a_mostrar:
        cols_macro = st.columns(len(semanas_a_mostrar))
        for i, sem in enumerate(semanas_a_mostrar):
            df_sem = df_filtered[df_filtered['Semana'] == sem]
            ing = df_sem['Total_Ingresos'].sum()
            hab = df_sem['Habilitadas'].sum()
            ubi = df_sem['Ubicadas'].sum()
            met = df_sem['Meta_Rec'].sum()
            rea = df_sem['Real_Rec'].sum()
            
            pct_hab = (hab/ing*100) if ing > 0 else 0
            pct_ubi = (ubi/ing*100) if ing > 0 else 0
            pct_rec = (rea/met*100) if met > 0 else 0
            
            with cols_macro[i]:
                st.markdown(f'<div class="macro-card-header">{sem}</div>', unsafe_allow_html=True)
                st.markdown(f"""
                    <div class="macro-card-body">
                        <p class="macro-label">📥 Ingresos</p><p class="macro-value">{ing:,.0f}</p>
                        <div class="macro-divider"></div>
                        <p class="macro-label">✨ Habilitado</p><p class="macro-value">{hab:,.0f} <span class="macro-pct">({pct_hab:.1f}%)</span></p>
                        <div class="macro-divider"></div>
                        <p class="macro-label">📍 Ubicado</p><p class="macro-value">{ubi:,.0f} <span class="macro-pct">({pct_ubi:.1f}%)</span></p>
                        <div class="macro-divider"></div>
                        <p class="macro-label">🎯 % Recorridos</p><p class="macro-value">{pct_rec:.1f}%</p>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No hay datos suficientes para mostrar el resumen macro con los filtros actuales.")

    # --- GRÁFICOS ---
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<p class="graph-title">Ingresos vs Habilitado por Tienda</p>', unsafe_allow_html=True)
        df_g = df_filtered.groupby('Tienda').agg({'Total_Ingresos':'sum', 'Habilitadas':'sum'}).reset_index().sort_values('Total_Ingresos', ascending=False)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_g['Tienda'], y=df_g['Total_Ingresos'], name="Ingresos", marker_color='#1F497D'))
        fig.add_trace(go.Bar(x=df_g['Tienda'], y=df_g['Habilitadas'], name="Habilitado", marker_color='#E6007E'))
        fig.update_layout(barmode='group', plot_bgcolor='white', height=350, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.markdown('<p class="graph-title">Cumplimiento de Recorridos (%)</p>', unsafe_allow_html=True)
        df_r = df_filtered.groupby('Tienda').agg({'Real_Rec':'sum', 'Meta_Rec':'sum'}).reset_index()
        df_r['% Recorridos'] = (df_r['Real_Rec'] / df_r['Meta_Rec'] * 100).fillna(0)
        fig2 = go.Figure(go.Bar(x=df_r['Tienda'], y=df_r['% Recorridos'], marker_color='#1F497D', text=df_r['% Recorridos'].map('{:.1f}%'.format), textposition='auto'))
        fig2.update_layout(plot_bgcolor='white', height=350, margin=dict(t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    # --- MATRIZ DETALLADA (AGRUPADA POR SEMANA) ---
    st.markdown('<p class="graph-title">🔍 Matriz de Auditoría Detallada (Agrupada por Semana)</p>', unsafe_allow_html=True)
    df_matrix = df_filtered.groupby(['Semana', 'Tienda']).agg({
        'Total_Ingresos': 'sum',
        'Habilitadas': 'sum',
        'Ubicadas': 'sum',
        'Real_Rec': 'sum',
        'Meta_Rec': 'sum'
    }).reset_index()
    
    # Calcular porcentajes para la tabla
    df_matrix['% Habilitado'] = (df_matrix['Habilitadas'] / df_matrix['Total_Ingresos'] * 100).fillna(0).map('{:.1f}%'.format)
    df_matrix['% Ubicado'] = (df_matrix['Ubicadas'] / df_matrix['Total_Ingresos'] * 100).fillna(0).map('{:.1f}%'.format)
    df_matrix['% Recorridos'] = (df_matrix['Real_Rec'] / df_matrix['Meta_Rec'] * 100).fillna(0).map('{:.1f}%'.format)
    
    st.dataframe(df_matrix[['Semana', 'Tienda', 'Total_Ingresos', 'Habilitadas', '% Habilitado', 'Ubicadas', '% Ubicado', '% Recorridos']], use_container_width=True)

else:
    st.info("No se detectaron datos. Por favor, asegúrate de publicar el Google Sheet como Excel (.xlsx) y seleccionar 'Todo el documento'.")
