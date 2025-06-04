import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
from io import StringIO

st.set_page_config(page_title="Dashboard de Leads Baixada", layout="wide")
st.title("Dashboard de Leads Baixada")

# URL fixa - removendo o input da sidebar
github_url = "https://raw.githubusercontent.com/valdemirvasconcelos/leadsbaixada/main/leads_baixada.csv"

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

# Normaliza colunas
df.columns = df.columns.str.strip().str.lower()
df = df.copy()

# Função específica para converter lat/lng no formato brasileiro
def clean_lat_lng(serie: pd.Series) -> pd.Series:
    # Remove aspas e espaços, substitui vírgulas por pontos
    texto = serie.astype(str).str.strip().str.replace('"', '').str.replace(',', '.')
    return pd.to_numeric(texto, errors="coerce")

# Converte lat/lng para numérico
df.loc[:, "lat"] = clean_lat_lng(df["lat"])
df.loc[:, "lng"] = clean_lat_lng(df["lng"])

# Remove linhas com lat/lng nulos
df = df.dropna(subset=['lat', 'lng'])

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

# Exibe tabela sem lat/lng
st.subheader(f"📊 {len(df_filt)} leads filtrados")
cols_exibir = [col for col in df_filt.columns if col not in ["lat", "lng", "unnamed: 11"]]
st.dataframe(df_filt[cols_exibir])

# Gera mapa
if len(df_filt) > 0:
    map_center = [-23.9, -46.4]
    zoom_start = 10

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
                    radius=8,
                    color=color_map.get(cat, "gray"),
                    fill=True,
                    fill_color=color_map.get(cat, "gray"),
                    fill_opacity=0.8,
                    popup=f"<b>{row.get('nome', 'Sem nome')}</b><br>Categoria: {cat}<br>Município: {row.get('municipio', '')}<br>Avaliação: {row.get('avaliacao', 'N/A')}"
                ).add_to(m)

        st_folium(m, width=900, height=650)

        # Legenda na sidebar
        st.sidebar.subheader("🎨 Legenda de Cores")
        for cat, cor in color_map.items():
            if cat in cat_selecionadas:
                st.sidebar.markdown(f"<span style='color:{cor}; font-size: 20px;'>●</span> {cat}", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Erro ao gerar o mapa: {e}")
else:
    st.info("Nenhum lead encontrado com os filtros selecionados.")
