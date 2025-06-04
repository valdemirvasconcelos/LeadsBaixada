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
        return pd.read_csv(filename)
    except Exception:
        return None

def validate_and_process_data(df, filename="leads_baixada.csv"):
    """Valida e processa tipos: mantém registros mesmo sem município/categoria,
       mas remove apenas linhas sem lat/lng válidos."""
    if df is None:
        return None

    required_cols = ["nome", "endereco", "municipio", "categoria", "lat", "lng"]
    if not all(col in df.columns for col in required_cols):
        st.error(f"Erro: faltam colunas obrigatórias: {', '.join(required_cols)}")
        return None

    df2 = df.copy()
    # garante formato numérico em lat/lng
    df2["lat"] = pd.to_numeric(df2["lat"].astype(str).str.replace(",", "."), errors="coerce")
    df2["lng"] = pd.to_numeric(df2["lng"].astype(str).str.replace(",", "."), errors="coerce")
    # remove só onde lat OU lng forem NaN
    df2 = df2.dropna(subset=["lat", "lng"])

    # cast segurança
    df2["municipio"] = df2["municipio"].astype(str)
    df2["categoria"] = df2["categoria"].astype(str).str.strip()

    # colunas opcionais
    for col in ["avaliacao", "numero_avaliacoes", "telefone", "website"]:
        if col not in df2:
            df2[col] = None

    return df2

def generate_color_map_folium(categories):
    """Mapa de cores, com alguns fixes e MD5 para o resto."""
    fixed = {
        "Bar/Casa Noturna": "#00FFFF",
        "Adega": "#DAA520",
        "bar": "#FF6347",
        "casa noturna": "#8A2BE2"
    }
    palette = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
        "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
        "#bcbd22", "#17becf"
    ]
    cmap = {}
    idx = 0
    for cat in sorted(categories):
        if cat in fixed:
            cmap[cat] = fixed[cat]
        else:
            try:
                h = hashlib.md5(cat.encode()).hexdigest()[:6]
                cmap[cat] = f"#{h}"
            except:
                cmap[cat] = palette[idx % len(palette)]
                idx += 1
    # garante
    if "Bar/Casa Noturna" not in cmap:
        cmap["Bar/Casa Noturna"] = "#00FFFF"
    return cmap

# --- Interface Streamlit ---
st.title("🗺️ Dashboard de Leads - Gelo com Sabores (Folium)")

# --- Carregamento e Validação ---
csv_file = "leads_baixada.csv"
if not os.path.isfile(csv_file):
    st.error("Arquivo de dados não encontrado.")
    st.warning("Coloque 'leads_baixada.csv' na raiz do app.")
    try:
        st.warning(f"Arquivos no dir: {os.listdir('.')}")
    except:
        pass
    df = None
else:
    raw = read_csv_cached(csv_file)
    df = validate_and_process_data(raw, csv_file)

# --- Se dados OK, cria filtros e tabela ---
if df is not None:
    # colunas da tabela
    base = ["nome", "endereco", "municipio", "categoria", "avaliacao", "numero_avaliacoes"]
    contacts = [c for c in ["telefone", "website"] if c in df and df[c].notna().any()]
    display = base + contacts

    st.sidebar.header("⚙️ Filtros")
    mun_options = sorted(df["municipio"].unique())
    cat_options = sorted(df["categoria"].unique())

    mun_sel = st.sidebar.multiselect("Municípios", mun_options, default=mun_options)
    cat_sel = st.sidebar.multiselect("Categorias", cat_options, default=cat_options)

    st.sidebar.header("🎨 Opções do Mapa")
    tile_sel = st.sidebar.selectbox("Tile do Folium", ["OpenStreetMap"], index=0)  # fixado
    radius = st.sidebar.slider("Tamanho (px)", 1, 15, 5)

    # aplica filtros
    sel = df[df["municipio"].isin(mun_sel)]
    if cat_sel:
        sel = sel[sel["categoria"].isin(cat_sel)]

    st.subheader(f"📊 {len(sel)} leads selecionados")
    df_show = sel[display].fillna("N/A")
    st.data_editor(df_show, hide_index=True)

    # --- Mapa ---
    if not sel.empty:
        st.subheader("📍 Mapa de Localização (Folium)")

        # já removemos NaN de lat/lng na validação, mas garantimos de novo
        sel_map = sel.dropna(subset=["lat", "lng"])
        if sel_map.empty:
            st.info("ℹ️ Nenhum ponto com coordenadas válidas para mostrar no mapa.")
        else:
            # calcula centro e zoom
            mc = [sel_map["lat"].mean(), sel_map["lng"].mean()]
            ld = sel_map["lat"].max() - sel_map["lat"].min()
            lg = sel_map["lng"].max() - sel_map["lng"].min()
            if ld < 0.1 and lg < 0.1:
                z = 13
            elif ld < 0.5 and lg < 0.5:
                z = 11
            else:
                z = 10

            m = folium.Map(location=mc, zoom_start=z, tiles=tile_sel)

            cmap = generate_color_map_folium(sel_map["categoria"].unique())

            for _, r in sel_map.iterrows():
                pop = (
                    f"<b>{r['nome']}</b><br>"
                    f"{r['endereco']}<br>"
                    f"<i>{r['categoria']}</i><br>"
                    f"Avaliação: {r.get('avaliacao','N/A')} ({int(r.get('numero_avaliacoes',0))} avaliações)<br>"
                    f"Telefone: {r.get('telefone','N/A')}<br>"
                    f"Site: {r.get('website','N/A')}"
                )
                iframe = folium.IFrame(pop, width=250, height=140)
                folium.CircleMarker(
                    location=[r["lat"], r["lng"]],
                    radius=radius,
                    popup=folium.Popup(iframe),
                    color=cmap.get(r["categoria"], "#808080"),
                    fill=True, fill_color=cmap.get(r["categoria"], "#808080"), fill_opacity=0.7
                ).add_to(m)

            st_folium(m, width=1000, height=650)

            st.sidebar.subheader("Legenda de Cores")
            for cat in sorted(sel_map["categoria"].unique()):
                color = cmap.get(cat, "#808080")
                st.sidebar.markdown(f"<span style='color:{color};font-size:20px;'>●</span> {cat}", unsafe_allow_html=True)

    else:
        st.info("ℹ️ Nenhum lead encontrado para os filtros selecionados.")

else:
    st.error("Falha no carregamento ou processamento dos dados.")
