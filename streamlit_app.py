import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from io import BytesIO

# =========================================================================
# --- CONFIGURACIÓN EJECUTIVA Y ESTILOS ---
# =========================================================================
st.set_page_config(page_title="Price Shoes - Intelligence Master DB", layout="wide", page_icon="👚")

st.markdown("""
    <style>
    .main-title { color: #000000; font-size: 34px; font-weight: 900; margin-bottom: 0px; }
    .sub-title { color: #E6007E; font-size: 14px; font-weight: 800; margin-top: -5px; text-transform: uppercase; }
    .section-header { color: #1F497D; font-weight: 800; font-size: 18px; margin-top: 25px; margin-bottom: 10px; border-left: 5px solid #E6007E; padding-left: 10px; }
    
    /* Tarjetas WoW */
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
# --- MOTOR DE DATOS (GOOGLE DRIVE CSV) ---
# =========================================================================
@st.cache_data(ttl=600)
def load_master_db():
    # ID del archivo CSV compartido en Google Drive
    FILE_ID = "15UBabZ8g_VbDMZiPfR2iuW-U9YuNgHWP"
    URL = f"https://drive.google.com/uc?export=download&id={FILE_ID}"
    
    try:
        response = requests.get(URL, timeout=60)
        df = pd.read_csv(BytesIO(response.content), encoding='latin1', low_memory=False)
        
        # Limpieza de columnas
        df.columns = [c.strip() for c in df.columns]
        
        # Convertir fecha a datetime
        # El formato en el CSV parece ser YYYY-MM-DD HH:MM:SS en la columna 'Fecha'
        df['Fecha_dt'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df = df.dropna(subset=['Fecha_dt'])
        
        # Extraer Semana y Mes
        df['Semana'] = "Sem " + df['Fecha_dt'].dt.isocalendar().week.astype(str)
        meses_dict = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
        df['Mes'] = df['Fecha_dt'].dt.month.map(meses_dict)
        
        # Renombrar Ubicación para consistencia
        df = df.rename(columns={'Ubicación': 'Tienda', 'Número de Piezas': 'Pzas'})
        
        # Pivotar para obtener indicadores por fila operativa
        # Mapeo:
        # Ingreso = Actividad 'Ingreso'
        # Habilitado = Actividad 'Acondicionado'
        # Ubicado = Actividad 'Ubicado'
        # Recorridos = Actividad 'Recolección de muertos' y RECORRIDOs == 1
        
        df['Es_Ingreso'] = df.apply(lambda r: r['Pzas'] if r['Actividad Realizada'] == 'Ingreso' else 0, axis=1)
        df['Es_Hab'] = df.apply(lambda r: r['Pzas'] if r['Actividad Realizada'] == 'Acondicionado' else 0, axis=1)
        df['Es_Ubi'] = df.apply(lambda r: r['Pzas'] if r['Actividad Realizada'] == 'Ubicado' else 0, axis=1)
        df['Es_Rec'] = df.apply(lambda r: 1 if (r['Actividad Realizada'] == 'Recolección de muertos' and str(r['RECORRIDOs']) == '1') else 0, axis=1)
        
        return df
    except Exception as e:
        st.error(f"Error al conectar con la Base de Datos: {e}")
        return pd.DataFrame()

df_raw = load_master_db()

# --- HEADER ---
st.markdown('<p class="main-title">PRICE SHOES • Master Database Intelligence</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">CONTROL OPERATIVO INTEGRAL (CAMBIOS Y MUERTOS)</p>', unsafe_allow_html=True)

if not df_raw.empty:
    # --- FILTROS ---
    st.sidebar.markdown("### 🔍 Filtros de Reporte")
    
    meses_presentes = sorted(df_raw['Mes'].unique().tolist(), key=lambda x: ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'].index(x))
    sel_mes = st.sidebar.selectbox("Periodo Mensual:", ["Anual"] + meses_presentes)
    
    df_m = df_raw if sel_mes == "Anual" else df_raw[df_raw['Mes'] == sel_mes]
    
    semanas = ["Todas las Semanas"] + sorted(df_m['Semana'].unique().tolist(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    sel_sem = st.sidebar.selectbox("Corte Semanal:", semanas)
    
    tiendas = ["Consolidado"] + sorted(df_raw['Tienda'].unique().tolist())
    sel_tienda = st.sidebar.selectbox("Unidad de Negocio:", tiendas)

    # Filtrado Final
    df_f = df_m.copy()
    if sel_sem != "Todas las Semanas": df_f = df_f[df_f['Semana'] == sel_sem]
    if sel_tienda != "Consolidado": df_f = df_f[df_f['Tienda'] == sel_tienda]

    # --- TARJETAS WoW (DINÁMICAS) ---
    st.markdown('<p class="section-header">📊 Resumen Ejecutivo WoW (Dinámico)</p>', unsafe_allow_html=True)
    
    all_weeks = sorted(df_raw['Semana'].unique().tolist(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    # Si filtramos por mes, solo mostramos las semanas de ese mes
    weeks_to_show = sorted(df_f['Semana'].unique().tolist(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))[-4:]
    
    if weeks_to_show:
        cols_w = st.columns(len(weeks_to_show))
        for i, sem in enumerate(weeks_to_show):
            # Actual
            df_curr = df_raw[(df_raw['Semana'] == sem)]
            if sel_tienda != "Consolidado": df_curr = df_curr[df_curr['Tienda'] == sel_tienda]
            
            ing = df_curr['Es_Ingreso'].sum()
            hab = df_curr['Es_Hab'].sum()
            ubi = df_curr['Es_Ubi'].sum()
            rec = df_curr['Es_Rec'].sum()
            
            # Anterior para tendencia
            idx = all_weeks.index(sem)
            if idx > 0:
                sem_p = all_weeks[idx-1]
                df_prev = df_raw[(df_raw['Semana'] == sem_p)]
                if sel_tienda != "Consolidado": df_prev = df_prev[df_prev['Tienda'] == sel_tienda]
                
                ing_p, hab_p, ubi_p, rec_p = df_prev['Es_Ingreso'].sum(), df_prev['Es_Hab'].sum(), df_prev['Es_Ubi'].sum(), df_prev['Es_Rec'].sum()
                
                def trend(c, p):
                    if p == 0: return "—", "trend-neutral"
                    d = ((c-p)/p)*100
                    if d > 0.5: return f"▲ {d:.1f}%", "trend-up"
                    if d < -0.5: return f"▼ {abs(d):.1f}%", "trend-down"
                    return "● 0%", "trend-neutral"
                
                t_ing, c_ing = trend(ing, ing_p)
                t_hab, c_hab = trend(hab, hab_p)
                t_ubi, c_ubi = trend(ubi, ubi_p)
                t_rec, c_rec = trend(rec, rec_p)
            else:
                t_ing = t_hab = t_ubi = t_rec = "—"
                c_ing = c_hab = c_ubi = c_rec = "trend-neutral"

            with cols_w[i]:
                st.markdown(f'<div class="wow-card-header">{sem}</div>', unsafe_allow_html=True)
                st.markdown(f"""
                    <div class="wow-card-body">
                        <div class="wow-metric-row"><span class="wow-label">Ingresos</span><span class="wow-value">{ing:,.0f}</span><span class="wow-trend {c_ing}">{t_ing}</span></div>
                        <div class="wow-metric-row"><span class="wow-label">Habilitado</span><span class="wow-value">{hab:,.0f}</span><span class="wow-trend {c_hab}">{t_hab}</span></div>
                        <div class="wow-metric-row"><span class="wow-label">Ubicado</span><span class="wow-value">{ubi:,.0f}</span><span class="wow-trend {c_ubi}">{t_ubi}</span></div>
                        <div class="wow-metric-row"><span class="wow-label">Recorridos</span><span class="wow-value">{rec:,.0f}</span><span class="wow-trend {c_rec}">{t_rec}</span></div>
                    </div>
                """, unsafe_allow_html=True)

    # --- ANÁLISIS GRÁFICO ---
    tab1, tab2 = st.tabs(["📈 TENDENCIAS", "🔍 AUDITORÍA"])
    
    with tab1:
        cg1, cg2 = st.columns(2)
        with cg1:
            st.markdown('<p class="section-header">Evolución de Ingresos vs Habilitado</p>', unsafe_allow_html=True)
            df_ev = df_f.groupby('Semana').agg({'Es_Ingreso':'sum', 'Es_Hab':'sum'}).reset_index()
            df_ev['n'] = df_ev['Semana'].apply(lambda x: int(''.join(filter(str.isdigit, x)) or 0))
            df_ev = df_ev.sort_values('n')
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(x=df_ev['Semana'], y=df_ev['Es_Ingreso'], name="Ingresos", line=dict(color='#1F497D', width=3)))
            fig1.add_trace(go.Scatter(x=df_ev['Semana'], y=df_ev['Es_Hab'], name="Habilitado", line=dict(color='#E6007E', width=3)))
            fig1.update_layout(plot_bgcolor='white', height=350, margin=dict(t=0, b=0))
            st.plotly_chart(fig1, use_container_width=True, config={'staticPlot': True})
            
        with cg2:
            st.markdown('<p class="section-header">Distribución Operativa por Tienda</p>', unsafe_allow_html=True)
            df_tienda = df_f.groupby('Tienda').agg({'Es_Ingreso':'sum', 'Es_Ubi':'sum'}).reset_index().sort_values('Es_Ingreso', ascending=False)
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=df_tienda['Tienda'], y=df_tienda['Es_Ingreso'], name="Ingreso", marker_color='#1F497D'))
            fig2.add_trace(go.Bar(x=df_tienda['Tienda'], y=df_tienda['Es_Ubi'], name="Ubicado", marker_color='#E6007E'))
            fig2.update_layout(barmode='group', plot_bgcolor='white', height=350)
            st.plotly_chart(fig2, use_container_width=True, config={'staticPlot': True})

    with tab2:
        st.markdown('<p class="section-header">Matriz Consolidada de Auditoría</p>', unsafe_allow_html=True)
        df_audit = df_f.groupby(['Mes', 'Semana', 'Tienda']).agg({
            'Es_Ingreso': 'sum', 'Es_Hab': 'sum', 'Es_Ubi': 'sum', 'Es_Rec': 'sum'
        }).reset_index()
        st.dataframe(df_audit, use_container_width=True)

else:
    st.info("📊 Conectando con la base de datos maestra en Google Drive...")
