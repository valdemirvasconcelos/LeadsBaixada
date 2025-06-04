import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import hashlib
import os

st.set_page_config(page_title="Dashboard de Leads - Folium", layout="wide")

# --- Funções Auxiliares ---

@st.cache_data
def read_csv_cached(filename="leads_baixada.csv"):
    """Tenta ler o CSV. Retorna o DataFrame ou None em caso de erro."""
    try:
        df = pd.read_csv(filename)
        return df
    except Exception:
        return None

def validate_and_process_data(df, filename="leads_baixada.csv"):
    """Valida o DataFrame carregado e processa os tipos de dados."""
    if df is None:
        return None  # Se a leitura falhou, não há o que validar
    try:
        required_cols = ["nome", "endereco", "municipio", "categoria", "lat", "lng"]
        if not all(col in df.columns for col in required_cols):
            st.error(f"Erro: o arquivo não contém as colunas necessárias: {', '.join(required_cols)}")
            return None

        # Remove coluna desnecessária
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

        # Converte lat e lng para o formato correto
        df["lat"] = pd.to_numeric(df["lat"].str.replace(',', '.'), errors="coerce")
        df["lng"] = pd.to_numeric(df["lng"].str.replace(',', '.'), errors="coerce")

        # Remove NaN nas colunas de município, categoria, lat e lng
        df = df.dropna(subset=["municipio", "categoria", "lat", "lng"])

        df_processed = df.copy()
        df_processed["municipio"] = df_processed["municipio"].astype(str)
        df_processed["categoria"] = df_processed["categoria"].astype(str).str.strip()

        for col in ["avaliacao", "numero_avaliacoes", "telefone", "website"]:
            if col not in df_processed.columns:
                df_processed[col] = None

        return df_processed

    except Exception as e:
        st.error(f"Erro ao processar os dados do arquivo '{filename}': {e}")
        return None

def generate_color_map_folium(categories):
    """Gera um mapa de cores HEX, com cor fixa para 'Bar/Casa Noturna'."""
    color_map = {}
    fixed_colors = {
        "Bar/Casa Noturna": "#00FFFF",  # Azul Cian
        "Adega": "#DAA520",             # Goldenrod
        "bar": "#FF6347",               # Tomato
        "casa noturna": "#8A2BE2"        # BlueViolet
    }
    other_colors_palette = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
    ]
    color_index = 0

    for category in sorted(list(categories)):
        if category in fixed_colors:
            color_map[category] = fixed_colors[category]
        else:
            try:
                hash_object = hashlib.md5(category.encode())
                hex_dig = hash_object.hexdigest()
                color_map[category] = f"#{hex_dig[:6]}"
            except Exception:
                color_map[category] = other_colors_palette[color_index % len(other_colors_palette)]
                color_index += 1

    if "Bar/Casa Noturna" not in color_map:
        color_map["Bar/Casa Noturna"] = "#00FFFF"

    return color_map

# --- Interface Streamlit ---
st.title("🗺️ Dashboard de Leads - Gelo com Sabores (Folium)")

# --- Carregamento e Validação dos Dados ---
csv_filename = "leads_baixada.csv"
if not os.path.isfile(csv_filename):
    st.error("Erro Crítico: arquivo de dados não encontrado.")
    st.warning("Verifique se o arquivo 'leads_baixada.csv' está no repositório e com este nome.")
    try:
        st.warning(f"Arquivos encontrados no diretório atual: {os.listdir('.')}")
    except Exception as list_e:
        st.warning(f"Não foi possível listar arquivos do diretório: {list_e}")
    df = None
else:
    df_raw = read_csv_cached(csv_filename)
    df = validate_and_process_data(df_raw, csv_filename)

# --- Continua apenas se os dados foram carregados e validados com sucesso ---
if df is not None:
    base_cols = ["nome", "endereco", "municipio", "categoria", "avaliacao", "numero_avaliacoes"]
    contact_cols = [c for c in ["telefone", "website"] if c in df.columns and df[c].notna().any()]
    display_cols = base_cols + contact_cols

    st.sidebar.header("⚙️ Filtros")
    all_cat_options = sorted(df["categoria"].unique())
    mun_options = sorted(df["municipio"].unique())

    mun_sel = st.sidebar.multiselect("Municípios", mun_options, default=mun_options)
    cat_sel = st.sidebar.multiselect("Categorias", all_cat_options, default=all_cat_options)

    st.sidebar.header("🎨 Opções do Mapa")
    selected_tile = "OpenStreetMap"  # Estilo do mapa fixo
    radius_size = st.sidebar.slider("Tamanho dos Pontos (pixels)", min_value=1, max_value=15, value=5, step=1)

    if not cat_sel:
        df_filt = df[df["municipio"].isin(mun_sel)].copy()
    else:
        df_filt = df[df["municipio"].isin(mun_sel) & df["categoria"].isin(cat_sel)].copy()

    st.subheader(f"📊 {len(df_filt)} leads selecionados")
    cols_to_show_in_table = [col for col in display_cols if col in df_filt.columns]
    df_display = df_filt[cols_to_show_in_table].fillna("N/A")
    st.data_editor(df_display, hide_index=True)

    if not df_filt.empty:
        st.subheader("📍 Mapa de Localização (Folium)")

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
            map_center = [-23.9, -46.4]  # Centro padrão
            zoom_start = 9

        m = folium.Map(location=map_center, zoom_start=zoom_start, tiles=selected_tile)
        color_map = generate_color_map_folium(df_filt["categoria"].unique())

        for idx, row in df_filt.iterrows():
            nome = row["nome"] if pd.notna(row["nome"]) else "Nome não disponível"
            endereco = row["endereco"] if pd.notna(row["endereco"]) else "Endereço não disponível"
            categoria = row["categoria"] if pd.notna(row["categoria"]) else "N/A"
            avaliacao = row["avaliacao"] if pd.notna(row["avaliacao"]) else "N/A"
            num_avaliacoes = int(row["numero_avaliacoes"]) if pd.notna(row["numero_avaliacoes"]) else 0
            telefone = row["telefone"] if pd.notna(row["telefone"]) else "Não informado"
            website = row["website"] if pd.notna(row["website"]) else "Não informado"
            website_link = f"<a href='{website}' target='_blank'>{website}</a>" if website != "Não informado" else "Não informado"

            popup_html = f"""<b>{nome}</b><br>
{endereco}<br>
<i>{categoria}</i><br>
Avaliação: {avaliacao} ({num_avaliacoes} avaliações)<br>
Telefone: {telefone}<br>
Website: {website_link}"""
            iframe = folium.IFrame(popup_html, width=250, height=150)
            popup = folium.Popup(iframe, max_width=250)

            marker_color = color_map.get(row["categoria"], "#808080")

            folium.CircleMarker(
                location=[row["lat"], row["lng"]],
                radius=radius_size,
                popup=popup,
                tooltip=nome,
                color=marker_color,
                fill=True,
                fill_color=marker_color,
                fill_opacity=0.7
            ).add_to(m)

        # Exibe o mapa com tamanho fixo
        st_folium(m, width=1000, height=650)

        st.sidebar.subheader("Legenda de Cores")
        for category in sorted(df_filt["categoria"].unique()):
            color_hex = color_map.get(category, "#808080")
            st.sidebar.markdown(
                f"<span style='color:{color_hex}; font-size: 20px;'>●</span> {category}",
                unsafe_allow_html=True
            )

    elif df is not None:
        st.info("ℹ️ Nenhum lead encontrado para os filtros selecionados.")

elif df is None:
    st.error("Falha no carregamento ou processamento dos dados. Verifique as mensagens acima.")
