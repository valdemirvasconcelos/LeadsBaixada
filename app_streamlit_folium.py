import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import hashlib
import os # Ainda útil para mensagens de erro mais claras

st.set_page_config(page_title="Dashboard de Leads - Folium", layout="wide")

# --- Funções Auxiliares ---

# Modificada para carregar de um nome de arquivo fixo, com erro mais direto
@st.cache_data
def load_data_from_file(filename="leads_baixada.csv"):
    """Carrega dados do CSV local com tratamento de erro aprimorado."""
    # Verifica se o arquivo existe no caminho esperado (útil para debug no Streamlit Cloud)
    if not os.path.isfile(filename):
        st.error(f"Erro Crítico: Arquivo de dados 
ão encontrado.")
        st.warning(f"Verifique se o arquivo 
aiz do repositório GitHub e tem exatamente este nome.")
        # Lista arquivos no diretório atual para ajudar no debug (pode ser comentado depois)
        try:
            st.warning(f"Arquivos encontrados no diretório atual: {os.listdir('.')}")
        except Exception as list_e:
            st.warning(f"Não foi possível listar arquivos do diretório: {list_e}")
        return None
    try:
        df = pd.read_csv(filename)
        required_cols = ["nome", "endereco", "municipio", "categoria", "lat", "lng"]
        if not all(col in df.columns for col in required_cols):
            st.error(f"Erro: O arquivo 
as colunas: {", ".join(required_cols)}")
            return None
        # Garante tipos corretos
        df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
        df["lng"] = pd.to_numeric(df["lng"], errors="coerce")
        df = df.dropna(subset=["lat", "lng"])
        df["municipio"] = df["municipio"].astype(str)
        df["categoria"] = df["categoria"].astype(str).str.strip()
        # Trata colunas opcionais
        for col in ["avaliacao", "numero_avaliacoes", "telefone", "website"]:
             if col not in df.columns:
                 df[col] = None
        return df
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o arquivo 

def generate_color_map_folium(categories):
    """Gera um mapa de cores HEX, com cor fixa para 'Bar/Casa Noturna'."""
    color_map = {}
    # Cores pré-definidas para consistência e melhor visualização
    # (Pode adicionar mais categorias fixas se desejar)
    fixed_colors = {
        "Bar/Casa Noturna": "#00FFFF", # Azul Cian
        "Adega": "#DAA520",        # Goldenrod (Amarelo Ouro)
        "bar": "#FF6347",          # Tomato (Vermelho Tomate)
        "casa noturna": "#8A2BE2"   # BlueViolet (Violeta Azulado)
    }
    # Paleta para categorias não definidas (baseada em hash, como antes)
    other_colors_palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", 
                            "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
    color_index = 0

    for category in sorted(list(categories)): # Ordena para consistência
        if category in fixed_colors:
            color_map[category] = fixed_colors[category]
        else:
            # Usa hash para tentar manter consistência, mas com fallback para paleta
            try:
                hash_object = hashlib.md5(category.encode())
                hex_dig = hash_object.hexdigest()
                color_map[category] = f"#{hex_dig[:6]}"
            except Exception:
                 # Fallback para paleta se hash falhar ou gerar cor inválida
                 color_map[category] = other_colors_palette[color_index % len(other_colors_palette)]
                 color_index += 1
                 
    # Garante que Bar/Casa Noturna SEMPRE seja Cian, mesmo que não esteja nas categorias selecionadas inicialmente
    # Isso é útil se a função for chamada com um subconjunto de categorias
    if "Bar/Casa Noturna" not in color_map:
         color_map["Bar/Casa Noturna"] = "#00FFFF"
         
    return color_map

# --- Interface Streamlit ---
st.title("🗺️ Dashboard de Leads - Gelo com Sabores (Folium)")

# --- Carregamento Automático dos Dados ---
df = load_data_from_file() # Tenta carregar diretamente o CSV

# --- Continua apenas se os dados foram carregados com sucesso ---
if df is not None:
    # Colunas a serem exibidas na tabela
    base_cols = ["nome", "endereco", "municipio", "categoria", "avaliacao", "numero_avaliacoes"]
    contact_cols = [c for c in ["telefone", "website"] if c in df.columns and df[c].notna().any()]
    display_cols = base_cols + contact_cols

    # --- Filtros na Barra Lateral ---
    st.sidebar.header("⚙️ Filtros")
    # Garante que as opções de categoria venham do DataFrame carregado
    all_cat_options = sorted(df["categoria"].unique())
    mun_options = sorted(df["municipio"].unique())

    mun_sel = st.sidebar.multiselect("Municípios", mun_options, default=mun_options)
    # Usa as categorias do DF como opções
    cat_sel = st.sidebar.multiselect("Categorias", all_cat_options, default=all_cat_options)

    # --- Opções de Visualização do Mapa ---
    st.sidebar.header("🎨 Opções do Mapa")
    map_tiles_options = [
        "OpenStreetMap", "CartoDB positron", "CartoDB dark_matter",
        "Stamen Terrain", "Stamen Toner", "Stamen Watercolor"
    ]
    selected_tile = st.sidebar.selectbox("Estilo do Mapa (Tile)", map_tiles_options, index=0) # Default OpenStreetMap
    radius_size = st.sidebar.slider("Tamanho dos Pontos (pixels)", min_value=1, max_value=15, value=5, step=1)

    # --- Aplicação dos Filtros ---
    # Garante que o filtro use as categorias selecionadas
    if not cat_sel: # Se nada for selecionado, considera tudo (ou pode optar por não mostrar nada)
        df_filt = df[df["municipio"].isin(mun_sel)].copy()
    else:
        df_filt = df[df["municipio"].isin(mun_sel) & df["categoria"].isin(cat_sel)].copy()

    # --- Exibição da Tabela --- 
    st.subheader(f"📊 {len(df_filt)} leads selecionados")
    cols_to_show_in_table = [col for col in display_cols if col in df_filt.columns]
    df_display = df_filt[cols_to_show_in_table].fillna("N/A")
    # Usar st.data_editor para permitir ordenação na interface
    st.data_editor(df_display, hide_index=True)

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

        # Gera mapa de cores para TODAS as categorias do DF filtrado
        # para garantir que a legenda e as cores sejam consistentes
        color_map = generate_color_map_folium(df_filt["categoria"].unique())

        # Adiciona marcadores
        for idx, row in df_filt.iterrows():
            nome = row["nome"] if pd.notna(row["nome"]) else "Nome não disponível"
            endereco = row["endereco"] if pd.notna(row["endereco"]) else "Endereço não disponível"
            categoria = row["categoria"] if pd.notna(row["categoria"]) else "N/A"
            avaliacao = row["avaliacao"] if pd.notna(row["avaliacao"]) else "N/A"
            num_avaliacoes = int(row["numero_avaliacoes"]) if pd.notna(row["numero_avaliacoes"]) else 0
            telefone = row["telefone"] if pd.notna(row["telefone"]) else "Não informado"
            website = row["website"] if pd.notna(row["website"]) else "Não informado"
            website_link = f"<a href=\'{website}\' target=\'_blank\'>{website}</a>" if website != "Não informado" else "Não informado"

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

            # Usa a cor do mapa de cores gerado
            marker_color = color_map.get(row["categoria"], "#808080") # Cinza como fallback

            folium.CircleMarker(
                location=[row["lat"], row["lng"]],
                radius=radius_size,
                popup=popup,
                tooltip=nome,
                color=marker_color, # Cor da borda
                fill=True,
                fill_color=marker_color, # Cor de preenchimento
                fill_opacity=0.7
            ).add_to(m)

        # Exibe o mapa - Mantendo o tamanho aumentado
        st_folium(m, width=1000, height=650)

        # --- Legenda de Cores --- 
        st.sidebar.subheader(" Legenda de Cores")
        # Mostra a legenda para as categorias PRESENTES no DF filtrado
        for category in sorted(df_filt["categoria"].unique()):
             color_hex = color_map.get(category, "#808080") # Pega a cor do mapa gerado
             st.sidebar.markdown(
                 f"<span style=\'color:{color_hex}; font-size: 20px;\'>●</span> {category}",
                 unsafe_allow_html=True
             )

    elif not df.empty:
        st.info("ℹ️ Nenhum lead encontrado para os filtros selecionados.")

# Mensagem caso o carregamento inicial falhe (df is None)
else:
    st.error("Não foi possível carregar os dados iniciais. Verifique os logs ou o nome/localização do arquivo CSV no repositório.")


