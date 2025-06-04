import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
from io import StringIO

st.set_page_config(page_title="Dashboard de Leads Baixada", layout="wide")
st.title("Dashboard de Leads Baixada")

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

df.columns = df.columns.str.strip().str.lower()
df = df.copy()

def clean_coordinates(serie):
    """Limpa coordenadas no formato específico do CSV"""
    def fix_coord(val):
        if pd.isna(val):
            return None
        
        val_str = str(val).strip().replace('"', '')
        
        # Remove todas as vírgulas primeiro
        clean_val = val_str.replace(',', '')
        
        # Tenta diferentes formatos baseados no comprimento
        try:
            num = float(clean_val)
            
            # Para latitude (deve estar entre -90 e 90)
            if -900000000 < num < -100000000:  # formato -239609694
                return num / 10000000  # -23.9609694
            elif -100000000 < num < -10000000:  # formato -23964431
                return num / 1000000   # -23.964431
            elif -10000000 < num < -1000000:   # formato -2396431
                return num / 100000    # -23.96431
            
            # Para longitude (deve estar entre -180 e 180)
            elif -5000000000000000000 < num < -1000000000000000:  # formato muito grande
                return num / 10000000000000000  # dividir por um fator grande
            elif -1000000000 < num < -100000000:  # formato -463692566
                return num / 10000000  # -46.3692566
            elif -100000000 < num < -10000000:   # formato -46369256
                return num / 1000000   # -46.369256
            
            # Se está na faixa normal de coordenadas, retorna como está
            elif -180 <= num <= 180:
                return num
                
        except:
            pass
            
        return None
    
    return serie.apply(fix_coord)

# Converte coordenadas
df['lat_numeric'] = clean_coordinates(df['lat'])
df['lng_numeric'] = clean_coordinates(df['lng'])

# Remove registros sem coordenadas válidas
df_with_coords = df.dropna(subset=['lat_numeric', 'lng_numeric']).copy()

# Filtros
municipios = sorted(df_with_coords["municipio"].dropna().unique())
mun_selecionados = st.sidebar.multiselect("Selecione municípios", options=municipios, default=municipios)

categorias = sorted(df_with_coords["categoria"].dropna().unique())
cat_selecionadas = st.sidebar.multiselect("Selecione categorias", options=categorias, default=categorias)

# Aplica filtros
df_filt = df_with_coords[
    (df_with_coords["municipio"].isin(mun_selecionados)) &
    (df_with_coords["categoria"].isin(cat_selecionadas))
].copy()

st.subheader(f"📊 {len(df_filt)} leads filtrados")
cols_exibir = [col for col in df_filt.columns if col not in ["lat", "lng", "lat_numeric", "lng_numeric", "unnamed: 11"]]
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
            lat, lng, cat = row["lat_numeric"], row["lng_numeric"], row["categoria"]
            nome = row.get('nome', 'Sem nome')
            
            if pd.notnull(lat) and pd.notnull(lng):
                folium.CircleMarker(
                    location=[lat, lng],
                    radius=8,
                    color=color_map.get(cat, "gray"),
                    fill=True,
                    fill_color=color_map.get(cat, "gray"),
                    fill_opacity=0.8,
                    popup=f"<b>{nome}</b><br>Categoria: {cat}<br>Município: {row.get('municipio', '')}<br>Avaliação: {row.get('avaliacao', 'N/A')}",
                    tooltip=nome  # AJUSTE ADICIONADO: tooltip mostra o nome ao passar o mouse
                ).add_to(m)

        st_folium(m, width=900, height=650)

        # Legenda
        st.sidebar.subheader("🎨 Legenda de Cores")
        for cat in sorted(df_filt["categoria"].unique()):
            cor = color_map.get(cat, "gray")
            st.sidebar.markdown(f"<span style='color:{cor}; font-size: 20px;'>●</span> {cat}", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Erro ao gerar o mapa: {e}")
        
else:
    st.info("Nenhum lead encontrado com os filtros selecionados.")
