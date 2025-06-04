import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
from io import StringIO

st.set_page_config(page_title="Dashboard de Leads Baixada", layout="wide")
st.title("Dashboard de Leads Baixada")

github_url_default = "https://raw.githubusercontent.com/valdemirvasconcelos/leadsbaixada/main/leads_baixada.csv"
github_url = st.sidebar.text_input("URL do arquivo CSV no GitHub", value=github_url_default)
st.markdown(f"Carregando dados da URL: [{github_url}]({github_url})")

@st.cache_data
def load_data(url: str) -> pd.DataFrame:
    try:
        response = requests.get(url)
        response.raise_for_status()
        csv_data = StringIO(response.text)
        # Separador vírgula e quotechar para aspas
        df = pd.read_csv(csv_data, sep=",", encoding="utf-8", quotechar='"')
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

df = load_data(github_url)
if df.empty:
    st.stop()

# Mostrar as colunas para debug (remova depois se quiser)
# st.write("Colunas encontradas no dataset:", df.columns.tolist())

# Normaliza colunas
df.columns = df.columns.str.strip().str.lower()
df = df.copy()

# --- Filtros sidebar ---

# Lista de municípios (cidades)
municipios = sorted(df["municipio"].dropna().unique())
mun_selecionados = st.sidebar.multiselect("Selecione municípios", options=municipios, default=municipios)

# Lista de categorias
categorias = sorted(df["categoria"].dropna().unique())
cat_selecionadas = st.sidebar.multiselect("Selecione categorias", options=categorias, default=categorias)

# Filtra dataframe
df_filt = df[
    (df["municipio"].isin(mun_selecionados)) &
    (df["categoria"].isin(cat_selecionadas))
].copy()

# Verifica colunas lat/lng ou alternativas
mostrar_mapa = True
if "lat" not in df_filt.columns or "lng" not in df_filt.columns:
    if {"latitude", "longitude"}.issubset(df_filt.columns):
        df_filt.rename(columns={"latitude": "lat", "longitude": "lng"}, inplace=True)
    else:
        mostrar_mapa = False
        st.warning("O dataset não contém colunas de coordenadas ('lat'/'lng' ou 'latitude'/'longitude'). O mapa não será exibido.")

def clean_numeric_col(serie: pd.Series) -> pd.Series:
    texto = serie.astype(str).str.replace(",", ".")
    return pd.to_numeric(texto, errors="coerce")

if mostrar_mapa:
    df_filt.loc[:, "lat"] = clean_numeric_col(df_filt["lat"])
    df_filt.loc[:, "lng"] = clean_numeric_col(df_filt["lng"])

# Exibe tabela sem lat/lng
st.subheader(f"📊 {len(df_filt)} leads filtrados")
cols_exibir = [col for col in df_filt.columns if col not in ["lat", "lng"]]
st.dataframe(df_filt[cols_exibir])

# Gera mapa
if mostrar_mapa:
    map_center = [-23.9, -46.4]
    zoom_start = 9

    def generate_color_map(categories) -> dict:
        palette = [
            "red", "blue", "green", "purple", "orange",
            "darkred", "lightblue", "beige", "darkgreen"
        ]
        unique = sorted(set(categories))
        return {cat: palette[i % len(palette)] for i, cat in enumerate(unique)}

    try:
        m = folium.Map(location=map_center, zoom_start=zoom_start, tiles="OpenStreetMap")
        color_map = generate_color_map(df_filt["categoria"])

        # Adiciona marcadores
        for _, row in df_filt.iterrows():
            lat, lng, cat = row["lat"], row["lng"], row["categoria"]
            if pd.notnull(lat) and pd.notnull(lng):
                folium.CircleMarker(
                    location=[float(lat), float(lng)],
                    radius=5,
                    color=color_map.get(cat, "gray"),
                    fill=True,
                    fill_color=color_map.get(cat, "gray"),
                    popup=f"{row.get('nome', 'Sem nome')}<br>Categoria: {cat}<br>Município: {row.get('municipio', '')}"
                ).add_to(m)

        st_folium(m, width=900, height=650)

        # Legenda na sidebar
        st.sidebar.subheader("Legenda de Cores")
        for cat, cor in color_map.items():
            if cat in cat_selecionadas:
                st.sidebar.markdown(f"<span style='color:{cor}; font-size: 20px;'>●</span> {cat}", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Erro ao gerar o mapa: {e}")
else:
    st.info("Exibindo somente os dados, pois não há colunas de coordenadas para gerar o mapa.")
