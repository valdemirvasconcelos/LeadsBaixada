import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import hashlib
import branca.colormap as cm # Para gerar cores
import os # Para verificar se o arquivo existe

st.set_page_config(page_title="Dashboard de Leads - Folium", layout="wide")

# --- Funções Auxiliares ---

# Modificada para carregar de um nome de arquivo fixo
@st.cache_data # Cache ainda útil para evitar recarregar a cada interação
def load_data_from_file(filename="leads_baixada.csv"):
    """Carrega dados do CSV local com tratamento de erro."""
    if not os.path.exists(filename):
        st.error(f"Erro Crítico: Arquivo de dados '{filename}' não encontrado no repositório.")
        st.warning("Certifique-se de que 'leads_baixada.csv' está na raiz do repositório GitHub junto com este script.")
        return None
    try:
        df = pd.read_csv(filename)
        required_cols = ["nome", "endereco", "municipio", "categoria", "lat", "lng"]
        if not all(col in df.columns for col in required_cols):
            st.error(f"Erro: O arquivo '{filename}' deve conter as colunas: {", ".join(required_cols)}")
            return None
        # Garante tipos corretos para colunas essenciais
        df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
        df["lng"] = pd.to_numeric(df["lng"], errors="coerce")
        df = df.dropna(subset=["lat", "lng"])
        df["municipio"] = df["municipio"].astype(str)
        df["categoria"] = df["categoria"].astype(str)
        # Trata colunas opcionais
        for col in ["avaliacao", "numero_avaliacoes", "telefone", "website"]:
             if col not in df.columns:
                 df[col] = None # Adiciona coluna vazia se não existir
        return df
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o arquivo '{filename}': {e}")
        return None

def generate_color_map_folium(categories):
    """Gera um mapa de cores HEX consistente para categorias usando hash."""
    color_map = {}
    for category in categories:
        hash_object = hashlib.md5(category.encode())
        hex_dig = hash_object.hexdigest()
        color_hex = f"#{hex_dig[:6]}"
        color_map[category] = color_hex
    return color_map

# --- Interface Streamlit ---

st.title("🗺️ Dashboard de Leads - Gelo com Sabores (Folium)")

# --- Carregamento Automático dos Dados ---
df = load_data_from_file() # Carrega diretamente o CSV

# --- Continua apenas se os dados foram carregados com sucesso ---
if df is not None:
    # Colunas a serem exibidas na tabela
    base_cols = ["nome", "endereco", "municipio", "categoria", "avaliacao", "numero_avaliacoes"]
    contact_cols = [c for c in ["telefone", "website"] if c in df.columns and df[c].notna().any()]
    display_cols = base_cols + contact_cols

    # --- Filtros na Barra Lateral ---
    st.sidebar.header("⚙️ Filtros")
    mun_options = sorted(df["municipio"].unique())
    cat_options = sorted(df["categoria"].unique())

    mun_sel = st.sidebar.multiselect("Municípios", mun_options, default=mun_options)
    cat_sel = st.sidebar.multiselect("Categorias", cat_options, default=cat_options)

    # --- Opções de Visualização do Mapa ---
    st.sidebar.header("🎨 Opções do Mapa")
    map_tiles_options = [
        "OpenStreetMap", "CartoDB positron", "CartoDB dark_matter",
        "Stamen Terrain", "Stamen Toner", "Stamen Watercolor"
    ]
    selected_tile = st.sidebar.selectbox("Estilo do Mapa (Tile)", map_tiles_options, index=1)
    radius_size = st.sidebar.slider("Tamanho dos Pontos (pixels)", min_value=1, max_value=15, value=5, step=1)

    # --- Aplicação dos Filtros ---
    df_filt = df.query("municipio in @mun_sel and categoria in @cat_sel").copy()

    # --- Exibição da Tabela --- 
    st.subheader(f"📊 {len(df_filt)} leads selecionados")
    cols_to_show_in_table = [col for col in display_cols if col in df_filt.columns]
    df_display = df_filt[cols_to_show_in_table].fillna("N/A")
    st.dataframe(df_display)

    # --- Exibição do Mapa com Folium ---
    if not df_filt.empty:
        st.subheader("📍 Mapa de Localização (Folium)")

        # Calcula centro do mapa
        try:
            map_center = [df_filt["lat"].mean(), df_filt["lng"].mean()]
            lat_diff = df_filt["lat"].max() - df_filt["lat"].min()
            lng_diff = df_filt["lng"].max() - df_filt["lng"].min()
            if lat_diff < 0.1 and lng_diff < 0.1:
                zoom_start = 13
            elif lat_diff < 0.5 and lng_diff < 0.5:
                zoom_start = 11
            else:
                zoom_start = 10
        except Exception:
            map_center = [-23.9, -46.4]
            zoom_start = 9

        # Cria o mapa Folium
        m = folium.Map(location=map_center, zoom_start=zoom_start, tiles=selected_tile)

        # Gera mapa de cores
        color_map = generate_color_map_folium(cat_sel)

        # Adiciona marcadores
        for idx, row in df_filt.iterrows():
            nome = row["nome"] if pd.notna(row["nome"]) else "Nome não disponível"
            endereco = row["endereco"] if pd.notna(row["endereco"]) else "Endereço não disponível"
            categoria = row["categoria"] if pd.notna(row["categoria"]) else "N/A"
            avaliacao = row["avaliacao"] if pd.notna(row["avaliacao"]) else "N/A"
            num_avaliacoes = int(row["numero_avaliacoes"]) if pd.notna(row["numero_avaliacoes"]) else 0
            telefone = row["telefone"] if pd.notna(row["telefone"]) else "Não informado"
            website = row["website"] if pd.notna(row["website"]) else "Não informado"
            website_link = f"<a href='{website}' target='_blank'>{website}</a>" if website != "Não informado" else "Não informado"

            popup_html = f"""
            <b>{nome}</b><br>
            {endereco}<br>
            <i>{categoria}</i><br>
            Avaliação: {avaliacao} ({num_avaliacoes} avaliações)<br>
            Telefone: {telefone}<br>
            Website: {website_link}
            """
            iframe = folium.IFrame(popup_html, width=250, height=150)
            popup = folium.Popup(iframe, max_width=250)

            folium.CircleMarker(
                location=[row["lat"], row["lng"]],
                radius=radius_size,
                popup=popup,
                tooltip=nome,
                color=color_map.get(row["categoria"], "#808080"),
                fill=True,
                fill_color=color_map.get(row["categoria"], "#808080"),
                fill_opacity=0.7
            ).add_to(m)

        # Exibe o mapa
        st_folium(m, width=1000, height=650)

        # --- Legenda de Cores --- 
        st.sidebar.subheader(" Legenda de Cores")
        for category, color_hex in color_map.items():
            if category in cat_sel:
                st.sidebar.markdown(
                    f"<span style='color:{color_hex}; font-size: 20px;'>●</span> {category}",
                    unsafe_allow_html=True
                )

    elif not df.empty:
        st.info("ℹ️ Nenhum lead encontrado para os filtros selecionados.")

# Mensagem caso o carregamento inicial falhe (df is None)
else:
    st.error("Não foi possível carregar os dados iniciais. Verifique os logs acima.")


