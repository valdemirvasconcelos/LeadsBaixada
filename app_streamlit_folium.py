import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium

# --- Configurações de página (DEVE ser a primeira chamada Streamlit) ---
st.set_page_config(page_title="Dashboard de Leads Baixada", layout="wide")

# --- Ação de sidebar: limpar cache ---
if st.sidebar.button("🔄 Limpar cache de dados"):
    st.cache_data.clear()
    st.sidebar.success("Cache limpo! Atualize a página (F5) para recarregar os dados.")

st.title("Dashboard de Leads Baixada")

# --- Função de carregamento de dados com cache ---
@st.cache_data
def load_data(filepath: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(filepath, sep=";", encoding="utf-8")
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo de dados: {e}")
        return pd.DataFrame()
    return df

# --- Função para limpar e converter colunas numéricas ---
def clean_numeric_col(serie: pd.Series) -> pd.Series:
    texto = serie.astype(str).str.replace(",", ".")
    return pd.to_numeric(texto, errors="coerce")

# --- Função para gerar paleta de cores por categoria ---
def generate_color_map(categories) -> dict:
    palette = [
        "red", "blue", "green", "purple", "orange",
        "darkred", "lightblue", "beige", "darkgreen"
    ]
    unique = sorted(set(categories))
    return {cat: palette[i % len(palette)] for i, cat in enumerate(unique)}

# --- Input do caminho do arquivo ---
filepath = st.sidebar.text_input(
    "Caminho do arquivo CSV", 
    value="dados/leads_baixada.csv"
)

df = load_data(filepath)
if df.empty:
    st.stop()

# --- Garante que trabalhamos em cópia para evitar SettingWithCopyWarning ---
df = df.copy()

# --- Valida e limpa colunas de lat e lng ---
if not {"lat", "lng"}.issubset(df.columns):
    st.error("O dataset não contém as colunas 'lat' e/ou 'lng'.")
    st.stop()

df.loc[:, "lat"] = clean_numeric_col(df["lat"])
df.loc[:, "lng"] = clean_numeric_col(df["lng"])

# --- Filtro de categoria ---
if "categoria" not in df.columns:
    st.error("O dataset não contém a coluna 'categoria'.")
    st.stop()

categorias = df["categoria"].dropna().unique().tolist()
selecionadas = st.sidebar.multiselect(
    "Selecione categorias para exibir", 
    options=categorias, 
    default=categorias
)
df_filt = df[df["categoria"].isin(selecionadas)].copy()

# --- Parâmetros do mapa ---
map_center = [-23.9, -46.4]  # lat, lng em float
zoom_start = 9

# --- Construção do mapa ---
try:
    m = folium.Map(location=map_center, zoom_start=zoom_start, tiles="OpenStreetMap")
    color_map = generate_color_map(df_filt["categoria"])

    for _, row in df_filt.iterrows():
        lat, lng, cat = row["lat"], row["lng"], row["categoria"]
        if pd.notnull(lat) and pd.notnull(lng):
            folium.CircleMarker(
                location=[float(lat), float(lng)],
                radius=5,
                color=color_map.get(cat, "gray"),
                fill=True,
                fill_color=color_map.get(cat, "gray"),
                popup=f"Categoria: {cat}"
            ).add_to(m)

    st_folium(m, width=800, height=600)
except Exception as e:
    st.error(f"Erro ao gerar o mapa: {e}")
