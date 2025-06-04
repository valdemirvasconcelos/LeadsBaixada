import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
from io import StringIO

# --- Configurações iniciais ---
st.set_page_config(page_title="Dashboard de Leads Baixada", layout="wide")
st.title("Dashboard de Leads Baixada")

# --- Função de carregamento de dados com cache ---
@st.cache_data
def load_data(github_url: str) -> pd.DataFrame:
    try:
        response = requests.get(github_url)
        response.raise_for_status()  # Garante que a requisição foi bem-sucedida
        csv_data = StringIO(response.text)
        df = pd.read_csv(csv_data, sep=";", encoding="utf-8")
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao baixar o arquivo do GitHub: {e}")
        return pd.DataFrame()
    except pd.errors.ParserError as e:
        st.error(f"Erro ao processar o arquivo CSV: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo de dados: {e}")
        return pd.DataFrame()
    return df

# --- Função para converter colunas numéricas ---
def clean_numeric_col(serie: pd.Series) -> pd.Series:
    texto = serie.astype(str).str.replace(",", ".")
    return pd.to_numeric(texto, errors="coerce")

# --- Função para gerar mapa de cores para as categorias ---
def generate_color_map(categories) -> dict:
    palette = [
        "red", "blue", "green", "purple", "orange",
        "darkred", "lightblue", "beige", "darkgreen"
    ]
    unique = sorted(set(categories))
    return {cat: palette[i % len(palette)] for i, cat in enumerate(unique)}

# --- Input da URL do CSV no GitHub ---
github_url = st.sidebar.text_input(
    "URL do arquivo CSV no GitHub",
    value="https://raw.githubusercontent.com/valdemirvasconcelos/leadsbaixada/main/leads_baixada.csv"
)

df = load_data(github_url)
if df.empty:
    st.stop()

# --- Normaliza os nomes das colunas (minúsculas e sem espaços extras) ---
df.columns = df.columns.str.strip().str.lower()

# --- Garante que trabalhamos em cópia para evitar SettingWithCopyWarning ---
df = df.copy()

# --- Verifica se a coluna "categoria" existe ---
if "categoria" not in df.columns:
    st.error("O dataset não contém a coluna 'categoria'.")
    st.stop()

# --- Filtro de categorias ---
categorias = df["categoria"].dropna().unique().tolist()
selecionadas = st.sidebar.multiselect(
    "Selecione categorias para exibir",
    options=categorias,
    default=categorias
)
df_filt = df[df["categoria"].isin(selecionadas)].copy()

# --- Verifica se as colunas de coordenadas estão presentes ou renomeia as alternativas ---
mostrar_mapa = True
if "lat" not in df_filt.columns or "lng" not in df_filt.columns:
    if {"latitude", "longitude"}.issubset(df_filt.columns):
        df_filt.rename(columns={"latitude": "lat", "longitude": "lng"}, inplace=True)
    else:
        mostrar_mapa = False
        st.warning("O dataset não contém colunas de coordenadas ('lat'/'lng' ou 'latitude'/'longitude'). O mapa não será exibido.")

# --- Se houver coordenadas, converte-as para numérico ---
if mostrar_mapa:
    df_filt.loc[:, "lat"] = clean_numeric_col(df_filt["lat"])
    df_filt.loc[:, "lng"] = clean_numeric_col(df_filt["lng"])

# --- Exibe dados em tabela (excluindo as colunas 'lat' e 'lng') ---
st.subheader("Dados dos Leads")
cols_exibir = [col for col in df_filt.columns if col not in ["lat", "lng"]]
st.dataframe(df_filt[cols_exibir])

# --- Geração e exibição do mapa ---
if mostrar_mapa:
    # Parâmetros padrão para o mapa
    map_center = [-23.9, -46.4]  # Coordenadas centrais
    zoom_start = 9
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
else:
    st.info("Exibindo somente os dados, pois não há colunas de coordenadas para gerar o mapa.")
