import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
from io import StringIO

st.set_page_config(page_title="Dashboard de Leads Baixada", layout="wide")
st.title("Dashboard de Leads Baixada")

# URL fixa (sem exibir para o usuário)
github_url = "https://raw.githubusercontent.com/valdemirvasconcelos/leadsbaixada/main/leads_baixada.csv"

@st.cache_data
def load_data(url: str) -> pd.DataFrame:
    try:
        response = requests.get(url)
        response.raise_for_status()
        csv_data = StringIO(response.text)
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

# --- FILTROS NA SIDEBAR ---
# Lista de municípios
municipios = sorted(df["municipio"].dropna().unique())
mun_selecionados = st.sidebar.multiselect("Selecione municípios", options=municipios, default=municipios)

# Lista de categorias
categorias = sorted(df["categoria"].dropna().unique())
cat_selecionadas = st.sidebar.multiselect("Selecione categorias", options=categorias, default=categorias)

# Aplica os filtros
df_filt = df[
    (df["municipio"].isin(mun_selecionados)) &
    (df["categoria"].isin(cat_selecionadas))
].copy()

# --- TABELA DOS DADOS ---
st.subheader(f"📊 {len(df_filt)} leads filtrados")
cols_exibir = [col for col in df_filt.columns if col not in ["lat", "lng", "unnamed: 11"]]
st.dataframe(df_filt[cols_exibir])

# --- PREPARAÇÃO PARA O MAPA ---
def clean_lat_lng(serie: pd.Series) -> pd.Series:
    """Converte coordenadas do formato brasileiro (com vírgulas) para decimal"""
    texto = serie.astype(str).str.strip().str.replace('"', '')
    
    def fix_coord(val):
        if pd.isna(val) or val == 'nan':
            return None
        val = str(val).replace(',', '')  # remove todas as vírgulas
        if len(val) > 6:
            return val[:-6] + '.' + val[-6:]  # insere ponto decimal
        else:
            return val
    
    texto = texto.apply(fix_coord)
    return pd.to_numeric(texto, errors='coerce')

# Converte coordenadas apenas para o mapa
if len(df_filt) > 0:
    df_mapa = df_filt.copy()
    df_mapa.loc[:, "lat"] = clean_lat_lng(df_mapa["lat"])
    df_mapa.loc[:, "lng"] = clean_lat_lng(df_mapa["lng"])
    
    # Remove leads sem coordenadas válidas
    df_mapa = df_mapa.dropna(subset=['lat', 'lng'])
    
    if len(df_mapa) > 0:
        # --- GERAÇÃO DO MAPA ---
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
            color_map = generate_color_map(df_mapa["categoria"])

            # Adiciona marcadores para cada lead filtrado
            for _, row in df_mapa.iterrows():
                lat, lng, cat = row["lat"], row["lng"], row["categoria"]
                nome = row.get('nome', 'Sem nome')
                municipio = row.get('municipio', '')
                avaliacao = row.get('avaliacao', 'N/A')
                
                folium.CircleMarker(
                    location=[lat, lng],
                    radius=8,
                    color=color_map.get(cat, "gray"),
                    fill=True,
                    fill_color=color_map.get(cat, "gray"),
                    fill_opacity=0.8,
                    popup=f"<b>{nome}</b><br>Categoria: {cat}<br>Município: {municipio}<br>Avaliação: {avaliacao}"
                ).add_to(m)

            st_folium(m, width=900, height=650)

            # --- LEGENDA NA SIDEBAR ---
            st.sidebar.subheader("🎨 Legenda de Cores")
            # Mostra apenas as categorias dos leads filtrados
            categorias_no_mapa = df_mapa["categoria"].unique()
            for cat in sorted(categorias_no_mapa):
                if cat in cat_selecionadas:
                    cor = color_map.get(cat, "gray")
                    st.sidebar.markdown(f"<span style='color:{cor}; font-size: 20px;'>●</span> {cat}", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erro ao gerar o mapa: {e}")
    else:
        st.info("Nenhum lead com coordenadas válidas encontrado para exibir no mapa.")
else:
    st.info("Nenhum lead encontrado com os filtros selecionados.")
