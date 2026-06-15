import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from io import BytesIO

# =====================================================
# ORION RECOVERY INTELLIGENCE - STREAMLIT CLOUD VERSION
# =====================================================

st.set_page_config(
    page_title="ORION Recovery Intelligence",
    layout="wide",
    page_icon="📈"
)

st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: Arial, sans-serif;
}
.main {
    background-color: #F4F7F9;
}
.metric-card {
    background: linear-gradient(135deg, #1F497D, #16355C);
    color: white;
    padding: 20px;
    border-radius: 14px;
    text-align: center;
}
.metric-label {
    font-size: 13px;
    opacity: .85;
    font-weight: bold;
}
.metric-value {
    font-size: 32px;
    font-weight: 900;
}
.section-title {
    color: #1F497D;
    font-size: 24px;
    font-weight: 900;
    border-bottom: 3px solid #E6007E;
    padding-bottom: 5px;
    margin-top: 25px;
}
</style>
""", unsafe_allow_html=True)


# =========================
# FUNCIONES BASE
# =========================

def to_num(val):
    try:
        if pd.isna(val) or val == "":
            return 0
        return float(str(val).replace("$", "").replace(",", "").replace(" ", ""))
    except:
        return 0


def safe_div(num, den):
    return num / den if den and den > 0 else 0


def clean_columns(df):
    df.columns = [str(c).strip() for c in df.columns]
    return df


def find_column(df, possible_names):
    cols = {str(c).strip().lower(): c for c in df.columns}
    for name in possible_names:
        if name.lower() in cols:
            return cols[name.lower()]
    return None


# =========================
# CARGA DE DATOS
# =========================

@st.cache_data(ttl=3600, show_spinner=False)
def load_excel(file):
    return pd.ExcelFile(file, engine="openpyxl")


def prepare_operacion(df):
    df = clean_columns(df)

    rename_map = {
        "Ubicación": "Tienda",
        "Ubicacion": "Tienda",
        "Piezas de Ingreso": "Total_Ing",
        "Piezas Ingreso": "Total_Ing",
        "Piezas Habilitadas": "Pzas_Hab",
        "Piezas Ubicadas": "Pzas_Ubi",
        "Recorridos Realizados": "Real_Rec",
        "Meta de Recorridos": "Meta_Rec"
    }

    df = df.rename(columns=rename_map)

    for col in ["Total_Ing", "Pzas_Hab", "Pzas_Ubi", "Real_Rec", "Meta_Rec"]:
        if col in df.columns:
            df[col] = df[col].apply(to_num)
        else:
            df[col] = 0

    if "Tienda" not in df.columns:
        df["Tienda"] = "Sin tienda"

    fecha_col = find_column(df, ["Fecha", "Dia", "Día"])
    if fecha_col:
        df["Fecha_DT"] = pd.to_datetime(df[fecha_col], errors="coerce")
        df["Semana"] = df["Fecha_DT"].dt.isocalendar().week.astype("Int64")
        df["Semana"] = df["Semana"].apply(lambda x: f"Sem {x}" if pd.notna(x) else "Sin semana")
        df["Mes"] = df["Fecha_DT"].dt.month_name()
    else:
        df["Semana"] = "Sin semana"
        df["Mes"] = "Sin mes"

    return df


def prepare_productividad(df):
    df = clean_columns(df)

    df = df.rename(columns={
        "Ubicación": "Tienda",
        "Ubicacion": "Tienda",
        "Numero de Piezas": "Pzas",
        "Número de Piezas": "Pzas",
        "Piezas": "Pzas"
    })

    if "Tienda" not in df.columns:
        df["Tienda"] = "Sin tienda"

    if "Pzas" not in df.columns:
        df["Pzas"] = 0

    df["Pzas"] = df["Pzas"].apply(to_num)

    if "Nombre" not in df.columns:
        posible_nombre = find_column(df, ["Colaborador", "Usuario", "Empleado", "Nombre Completo"])
        if posible_nombre:
            df["Nombre"] = df[posible_nombre]
        else:
            df["Nombre"] = "Sin colaborador"

    return df


def prepare_modelos(xls):
    sheet_mod = [
        s for s in xls.sheet_names
        if "venta" in s.lower() and "devol" in s.lower()
    ]

    if not sheet_mod:
        return pd.DataFrame()

    raw = pd.read_excel(
        xls,
        sheet_name=sheet_mod[0],
        header=None,
        engine="openpyxl"
    )

    try:
        fechas = raw.iloc[0].tolist()
        cabs = raw.iloc[1].tolist()

        def idx(name):
            for i, c in enumerate(cabs):
                if str(c).strip().lower() == name.lower():
                    return i
            return None

        idx_mod = idx("Modelo")
        idx_col = idx("Color")
        idx_mar = idx("Marca Price")
        idx_tie = idx("Tiendas")

        if None in [idx_mod, idx_col, idx_mar, idx_tie]:
            return pd.DataFrame()

        melted = []

        for i in range(25, len(cabs), 3):
            if i + 2 >= len(cabs):
                continue

            if pd.isna(fechas[i]):
                continue

            fecha = pd.to_datetime(fechas[i], errors="coerce")
            if pd.isna(fecha):
                continue

            subset = raw.iloc[2:, [idx_mod, idx_col, idx_mar, idx_tie, i, i + 1, i + 2]].copy()
            subset.columns = ["Modelo", "Color", "Marca", "Tienda", "Venta", "Dev", "Neta_$"]
            subset["Semana"] = f"Sem {fecha.isocalendar().week}"
            melted.append(subset)

        if not melted:
            return pd.DataFrame()

        df = pd.concat(melted, ignore_index=True)

        for col in ["Venta", "Dev", "Neta_$"]:
            df[col] = df[col].apply(to_num)

        return df

    except:
        return pd.DataFrame()


# =========================
# SIDEBAR
# =========================

st.sidebar.title("🎛️ ORION Control Center")

uploaded_file = st.sidebar.file_uploader(
    "Carga tu archivo Excel",
    type=["xlsx"]
)

st.sidebar.info(
    "Sube el archivo base de operaciones para iniciar el análisis."
)

# =========================
# INICIO
# =========================

st.title("📈 ORION Recovery Intelligence")
st.caption("Plataforma Nacional de Recuperación de Mercancía | Operaciones Ropa")

if uploaded_file is None:
    st.warning("Carga un archivo Excel para iniciar.")
    st.stop()

try:
    xls = load_excel(uploaded_file)
except Exception as e:
    st.error(f"No se pudo leer el archivo Excel: {e}")
    st.stop()

st.sidebar.success("Archivo cargado correctamente")

# =========================
# DETECCIÓN DE HOJAS
# =========================

sheet_names = xls.sheet_names

st.sidebar.markdown("### Hojas detectadas")
for s in sheet_names:
    st.sidebar.write(f"• {s}")

sheet_op = [
    s for s in sheet_names
    if "base" in s.lower() or "operacion" in s.lower() or "operación" in s.lower()
]

sheet_colab = [
    s for s in sheet_names
    if "colab" in s.lower() or "productividad" in s.lower() or "usuario" in s.lower()
]

if sheet_op:
    df_op_raw = pd.read_excel(xls, sheet_name=sheet_op[0], engine="openpyxl")
else:
    df_op_raw = pd.read_excel(xls, sheet_name=sheet_names[0], engine="openpyxl")

df_op = prepare_operacion(df_op_raw)

if sheet_colab:
    df_colab_raw = pd.read_excel(xls, sheet_name=sheet_colab[0], engine="openpyxl")
    df_colab = prepare_productividad(df_colab_raw)
else:
    df_colab = pd.DataFrame(columns=["Tienda", "Nombre", "Pzas"])

df_models = prepare_modelos(xls)

# =========================
# FILTROS
# =========================

weeks = sorted([w for w in df_op["Semana"].dropna().unique()])
stores = sorted([t for t in df_op["Tienda"].dropna().unique()])

sel_w = st.sidebar.multiselect(
    "Semanas",
    weeks,
    default=weeks
)

sel_s = st.sidebar.multiselect(
    "Tiendas",
    stores,
    default=stores
)

df_f = df_op[
    df_op["Semana"].isin(sel_w) &
    df_op["Tienda"].isin(sel_s)
]

df_cf = df_colab[
    df_colab["Tienda"].isin(sel_s)
] if not df_colab.empty else pd.DataFrame()

df_mf = df_models[
    df_models["Semana"].isin(sel_w) &
    df_models["Tienda"].isin(sel_s)
] if not df_models.empty else pd.DataFrame()


# =========================
# KPIS
# =========================

ing_t = df_f["Total_Ing"].sum()
hab_t = df_f["Pzas_Hab"].sum()
ubi_t = df_f["Pzas_Ubi"].sum()
rec_t = df_f["Real_Rec"].sum()

hab_pct = safe_div(hab_t, ing_t) * 100
ubi_pct = safe_div(ubi_t, ing_t) * 100

conv_g = 0
val_rec = 0

if not df_mf.empty:
    df_mf["Rec_Pzas"] = df_mf.apply(
        lambda r: min(r["Dev"], r["Venta"]),
        axis=1
    )
    conv_g = safe_div(df_mf["Rec_Pzas"].sum(), df_mf["Dev"].sum()) * 100
    df_mf["Rec_Val"] = df_mf.apply(
        lambda r: r["Neta_$"] * safe_div(min(r["Dev"], r["Venta"]), r["Venta"]),
        axis=1
    )
    val_rec = df_mf["Rec_Val"].sum()


# =========================
# TABS
# =========================

tabs = st.tabs([
    "🚀 Resumen Ejecutivo",
    "📦 Operación",
    "👥 Productividad",
    "📈 Conversión",
    "💰 Rentabilidad",
    "⚠️ Alertas",
    "🧾 Estructura del Archivo"
])


# =========================
# TAB 1
# =========================

with tabs[0]:
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Total Ingresos</div>
                <div class="metric-value">{ing_t:,.0f}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">% Habilitado</div>
                <div class="metric-value">{hab_pct:.1f}%</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">% Ubicado</div>
                <div class="metric-value">{ubi_pct:.1f}%</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Recuperación $</div>
                <div class="metric-value">${val_rec:,.0f}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown('<p class="section-title">Evolución Semanal</p>', unsafe_allow_html=True)

    wow = df_op.groupby("Semana", as_index=False)["Total_Ing"].sum()

    fig = px.area(
        wow,
        x="Semana",
        y="Total_Ing",
        title="Tendencia de Ingresos por Semana"
    )

    st.plotly_chart(fig, use_container_width=True)


# =========================
# TAB 2
# =========================

with tabs[1]:
    st.markdown('<p class="section-title">Funnel Operativo</p>', unsafe_allow_html=True)

    fig_funnel = go.Figure(go.Funnel(
        y=["Ingreso", "Habilitado", "Ubicado"],
        x=[ing_t, hab_t, ubi_t],
        textinfo="value+percent initial"
    ))

    st.plotly_chart(fig_funnel, use_container_width=True)

    st.markdown('<p class="section-title">Desempeño por Tienda</p>', unsafe_allow_html=True)

    resumen_tienda = (
        df_f.groupby("Tienda")
        .agg({
            "Total_Ing": "sum",
            "Pzas_Hab": "sum",
            "Pzas_Ubi": "sum",
            "Real_Rec": "sum"
        })
        .reset_index()
    )

    resumen_tienda["% Hab"] = resumen_tienda.apply(
        lambda r: safe_div(r["Pzas_Hab"], r["Total_Ing"]) * 100,
        axis=1
    )

    resumen_tienda["% Ubi"] = resumen_tienda.apply(
        lambda r: safe_div(r["Pzas_Ubi"], r["Total_Ing"]) * 100,
        axis=1
    )

    st.dataframe(resumen_tienda, use_container_width=True)


# =========================
# TAB 3
# =========================

with tabs[2]:
    st.markdown('<p class="section-title">Ranking de Productividad</p>', unsafe_allow_html=True)

    if not df_cf.empty:
        u_rank = (
            df_cf.groupby(["Nombre", "Tienda"], as_index=False)["Pzas"]
            .sum()
            .sort_values("Pzas", ascending=False)
        )

        c1, c2 = st.columns(2)

        with c1:
            st.subheader("Top 10")
            st.dataframe(u_rank.head(10), use_container_width=True)

        with c2:
            st.subheader("Bottom 10")
            st.dataframe(u_rank.tail(10), use_container_width=True)

        fig_prod = px.bar(
            u_rank.head(20),
            x="Nombre",
            y="Pzas",
            color="Tienda",
            title="Top 20 Productividad"
        )

        st.plotly_chart(fig_prod, use_container_width=True)

    else:
        st.warning("No se encontró hoja de productividad o colaboradores.")


# =========================
# TAB 4
# =========================

with tabs[3]:
    st.markdown('<p class="section-title">Conversión Comercial</p>', unsafe_allow_html=True)

    if not df_mf.empty:
        conv = (
            df_mf.groupby("Tienda")
            .apply(lambda x: safe_div(x["Rec_Pzas"].sum(), x["Dev"].sum()) * 100)
            .reset_index(name="Conv_%")
        )

        fig_conv = px.bar(
            conv.sort_values("Conv_%", ascending=False),
            x="Tienda",
            y="Conv_%",
            title="Conversión por Tienda"
        )

        st.plotly_chart(fig_conv, use_container_width=True)

        heat = (
            df_mf.groupby(["Tienda", "Semana"])
            .apply(lambda x: safe_div(x["Rec_Pzas"].sum(), x["Dev"].sum()) * 100)
            .unstack()
            .fillna(0)
        )

        fig_heat = px.imshow(
            heat,
            title="Heatmap Conversión Tienda / Semana"
        )

        st.plotly_chart(fig_heat, use_container_width=True)

    else:
        st.info("No se detectó hoja de venta y devolución.")


# =========================
# TAB 5
# =========================

with tabs[4]:
    st.markdown('<p class="section-title">Recuperación Económica</p>', unsafe_allow_html=True)

    if not df_mf.empty:
        rent = (
            df_mf.groupby("Tienda")
            .agg({
                "Neta_$": "sum",
                "Rec_Val": "sum"
            })
            .reset_index()
        )

        rent["Pendiente"] = rent["Neta_$"] - rent["Rec_Val"]

        fig_rent = go.Figure()

        fig_rent.add_trace(go.Bar(
            name="Recuperado",
            x=rent["Tienda"],
            y=rent["Rec_Val"]
        ))

        fig_rent.add_trace(go.Bar(
            name="Pendiente",
            x=rent["Tienda"],
            y=rent["Pendiente"]
        ))

        fig_rent.update_layout(
            barmode="stack",
            title="Recuperación vs Pendiente por Tienda"
        )

        st.plotly_chart(fig_rent, use_container_width=True)

        st.dataframe(rent, use_container_width=True)

    else:
        st.info("No hay información económica disponible.")


# =========================
# TAB 6
# =========================

with tabs[5]:
    st.markdown('<p class="section-title">Alertas Inteligentes</p>', unsafe_allow_html=True)

    if hab_pct < 80:
        st.error(f"⚠️ Habilitado bajo: {hab_pct:.1f}%")

    if ubi_pct < 80:
        st.error(f"⚠️ Ubicado bajo: {ubi_pct:.1f}%")

    if conv_g < 80 and not df_mf.empty:
        st.warning(f"⚠️ Conversión comercial baja: {conv_g:.1f}%")

    if ing_t == 0:
        st.error("🚨 No hay ingresos registrados con los filtros actuales.")

    if hab_pct >= 80 and ubi_pct >= 80:
        st.success("✅ Operación dentro de rango aceptable.")

    st.info("Revisa tiendas con menor porcentaje de habilitado, ubicado y productividad.")


# =========================
# TAB 7
# =========================

with tabs[6]:
    st.markdown('<p class="section-title">Estructura del Archivo</p>', unsafe_allow_html=True)

    estructura = []

    for sheet in sheet_names:
        try:
            temp = pd.read_excel(xls, sheet_name=sheet, nrows=5, engine="openpyxl")
            estructura.append({
                "Hoja": sheet,
                "Columnas": ", ".join([str(c) for c in temp.columns]),
                "Total Columnas": len(temp.columns)
            })
        except:
            estructura.append({
                "Hoja": sheet,
                "Columnas": "No se pudo leer",
                "Total Columnas": 0
            })

    st.dataframe(pd.DataFrame(estructura), use_container_width=True)

    st.download_button(
        "📥 Descargar datos filtrados CSV",
        df_f.to_csv(index=False).encode("utf-8"),
        "orion_reporte_filtrado.csv",
        "text/csv"
    )
