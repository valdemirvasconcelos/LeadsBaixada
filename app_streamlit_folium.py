import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import hashlib
import os

# ✅ Primeira chamada obrigatória
st.set_page_config(page_title="Dashboard de Leads Baixada", layout="wide")

# --- Funções ---

@st.cache_data
def read_csv_cached(filename="leads_baixada.csv"):
    try:
        df = pd.read_csv(filename)
        return df
    except Exception as e:
        st.error(f"Erro ao ler o arquivo CSV: {e}")
        return None

def validate_and_process_data(df):
    if df is None:
        return None
    try:
        df.columns = df.columns.str.lower()
        required_cols = ["nome", "endereco", "municipio", "categoria", "lat", "lng"]
        if not all(col in df.columns for col in required_cols):
            st.error("⚠️ Colunas faltando no CSV! Esperado: " + ", ".join(required_cols))
            st.warning("Colunas encontradas: " + ", ".join(df.columns))
            return None

        df_processed = df.copy()
        df_processed["lat"] = pd.to_numeric(df_processed["lat"], errors="coerce")
        df_processed["lng"] = pd.to_numeric(df_processed["lng"], errors="coerce")
        df_processed = df_processed.dropna(subset=["lat", "lng"])
        df_processed["municipio"] = df_processed["municipio"].astype(str)
        df_processed["categoria"] = df_processed["categoria"].astype(str).str.strip()

        for col in ["avaliacao", "numero_avaliacoes", "telefone", "website"]:
            if col not in df_processed.columns:
                df_processed[col] = None

        return df_processed
    except Exception as e:
        st.error(f"Erro ao processar os dados: {e}")
        return None

def generate_color_map_folium(categories):
    color_map = {}
    fixed_colors = {
        "Bar/Casa Noturna": "#00FFFF",
        "Adega": "#DAA520",
        "Bar": "#FF6347",
        "Casa Noturna": "#8A2BE2"
    }
    for category in sorted(categories):
        if category in fixed_colors:
            color_map[category] = fixed_colors[category]
        else:
            color_map[category] = "#" + hashlib.md5(category.encode()).hexdigest()[:6]
    return color_map

# --- Início do App ---

st.title("🗺️ Dashboard de Leads Baixada Santista")

csv_filename = "leads_baixada.csv"
df_raw = read_csv_cached(csv_filename)
df = validate_and_process_data(df_raw)

# 🔍 DEBUG TEMPORÁRIO
with st.expander("🛠️ Diagnóstico (Debug)"):
    if df_raw is not None:
        st.write("Primeiras linhas do CSV original:")
        st.dataframe(df_raw.head())
    if df is not None:
        st.write("Colunas válidas pós-processamento:")
        st.write(df.columns.tolist())
        st.write("Registros válidos:", len(df))

# --- Interface se dados forem válidos ---
if df is not None and not df.empty:
    base_cols = ["nome", "endereco", "municipio", "categoria", "avaliacao", "numero_avaliacoes"]
    contact_cols = [c for c in ["telefone", "website"] if c in df.columns and df[c].notna().any()]
    display_cols = base_cols + contact_cols

    st.sidebar.header("⚙️ Filtros")
    all_cat_options = sorted(df["categoria"].unique())
    mun_options = sorted(df["municipio"].unique())
    mun_sel = st.sidebar.multiselect("Municípios", mun_options, default=mun_options)
    cat_sel = st.sidebar.multiselect("Categorias", all_cat_options, default=all_cat_options)

    df_filt = df[df["municipio"].isin(mun_sel) & df["categoria"].isin(cat_sel)].copy()

    st.subheader(f"📊 {len(df_filt)} leads selecionados")
    st.dataframe(df_filt[display_cols].fillna("N/A"), use_container_width=True)

    if not df_filt.empty:
        st.subheader("📍 Mapa de Localização")
        map_center = [df_filt["lat"].mean(), df_filt["lng"].mean()]
        m = folium.Map(location=map_center, zoom_start=11, tiles="OpenStreetMap")
        color_map = generate_color_map_folium(df_filt["categoria"].unique())

        for _, row in df_filt.iterrows():
            popup = folium.Popup(f"{row['nome']}<br>{row['endereco']}", max_width=250)
            folium.CircleMarker(
                location=[row["lat"], row["lng"]],
                radius=5,
                popup=popup,
                tooltip=row["nome"],
                color=color_map.get(row["categoria"], "#666"),
                fill=True,
                fill_opacity=0.7
            ).add_to(m)

        st_folium(m, width=1000, height=600)
    else:
        st.info("Nenhum lead encontrado para os filtros selecionados.")
else:
    st.error("🚫 Nenhum dado válido foi carregado.")
