#!/usr/bin/env python3
"""
collector.py

Coleta leads de bares, adegas e casas noturnas na Baixada Santista
usando Google Places API.  
Enriquece com telefone e website e salva em CSV ou JSON.
Implementa cache para evitar chamadas repetidas à API.
"""

import os
import time
import argparse
import json

import googlemaps
import pandas as pd

# Municípios e categorias-alvo
MUNICIPIOS = {
    "Bertioga":   "Bertioga, SP",
    "Cubatão":    "Cubatão, SP",
    "Guarujá":    "Guarujá, SP",
    "Itanhaém":   "Itanhaém, SP",
    "Mongaguá":   "Mongaguá, SP",
    "Peruíbe":    "Peruíbe, SP",
    "Praia Grande":"Praia Grande, SP",
    "Santos":     "Santos, SP",
    "São Vicente":"São Vicente, SP",
}
CATEGORIAS = ["bar", "adega", "casa noturna"]

CACHE_FILE = "cache.json"

def carregar_cache():
    """Carrega dados do cache, se existir."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_cache(data):
    """Salva dados no cache."""
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def coletar_por_query(client, query):
    """Faz consulta por texto e retorna lista de places."""
    try:
        res = client.places(query=query, language="pt-BR")
        return res.get("results", [])
    except Exception as e:
        print(f"[ERRO] ao buscar '{query}': {e}")
        return []

def obter_detalhes_place(place_id, client):
    """Consulta Place Details para obter telefone e website."""
    try:
        detalhes = client.place(place_id=place_id, language="pt-BR")
        result = detalhes.get("result", {})
        telefone = result.get("formatted_phone_number")
        website = result.get("website")
        return telefone, website
    except Exception as e:
        print(f"[ERRO] detalhes place {place_id}: {e}")
        return None, None

def parse_place(place, municipio, categoria):
    """Extrai campos básicos de cada place."""
    loc = place.get("geometry", {}).get("location", {})
    return {
        "place_id": place.get("place_id"),
        "nome": place.get("name"),
        "endereco": place.get("formatted_address"),
        "municipio": municipio,
        "categoria": categoria,
        "avaliacao": place.get("rating"),
        "numero_avaliacoes": place.get("user_ratings_total"),
        "lat": loc.get("lat"),
        "lng": loc.get("lng"),
    }

def coletar_dados(api_key):
    """Itera sobre municípios e categorias, faz coleta e enriquecimento."""
    client = googlemaps.Client(key=api_key)
    todos = []
    cache = carregar_cache()

    for mun_key, mun_str in MUNICIPIOS.items():
        for cat in CATEGORIAS:
            query = f"{cat} em {mun_str}"
            if query in cache:
                print(f"[CACHE] Usando dados do cache para '{query}'")
                todos.extend(cache[query])
                continue

            print(f"[API] Coletando dados para '{query}'")
            results = coletar_por_query(client, query)
            dados = []

            for place in results:
                data = parse_place(place, mun_key, cat)
                telefone, website = obter_detalhes_place(data["place_id"], client)
                data["telefone"] = telefone
                data["website"] = website
                dados.append(data)
                time.sleep(1)  # respeita rate limit da API

            cache[query] = dados
            salvar_cache(cache)
            todos.extend(dados)
    
    return todos

def salvar_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[OK] Salvou {len(data)} registros em JSON em '{path}'.")

def salvar_csv(data, path):
    df = pd.DataFrame(data)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"[OK] Salvou {len(data)} registros em CSV em '{path}'.")

def main():
    parser = argparse.ArgumentParser(description="Coleta leads na Baixada Santista")
    parser.add_argument("--api-key", help="Chave da Google Places API")
    parser.add_argument(
        "--output-format", choices=["csv", "json"], default="csv",
        help="Formato de saída (csv ou json)"
    )
    parser.add_argument(
        "--output-file", default="leads_baixada",
        help="Nome base do arquivo de saída (sem extensão)"
    )
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[ERRO] Informe a chave com --api-key ou defina GOOGLE_API_KEY no ambiente.")
        return

    dados = coletar_dados(api_key)
    if not dados:
        print("[WARN] Nenhum dado coletado.")
        return

    out_path = f"{args.output_file}.{args.output_format}"
    if args.output_format == "json":
        salvar_json(dados, out_path)
    else:
        salvar_csv(dados, out_path)

if __name__ == "__main__":
    main()
