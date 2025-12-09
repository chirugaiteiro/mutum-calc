# fito_config.py
# -*- coding: utf-8 -*-

"""
Arquivo de configuração para o Módulo de Inventário e Fitossociologia (Mutum).
Contém listas oficiais, parâmetros de validação e dicionários de mapeamento.
"""

# --- 1. LISTAS DE ESPÉCIES (URLs e Dicionários Fixos) ---

# URL "Raw" do arquivo CSV no GitHub (Substitua pelo seu link real após o upload)
URL_LISTA_MMA_CSV = "https://github.com/chirugaiteiro/bases_ambientais/raw/refs/heads/main/flora-ameacada-2021.csv"

# Compensação Estadual (Resolução SEMADE n.9/2015 - Art. 52)
# Mantemos hardcoded pois é uma lista legal pequena e específica do MS
LISTA_IMASUL_COMPENSACAO = {
    # Nomes Comuns
    "PEROBA ROSA": 10, "CEDRO": 10, "CEDRO ROSA": 10, "JEQUITIBA": 10, 
    "ITAUBA": 10, "BARAUNA": 10, "QUEBRACHO": 10, "AROEIRA DO SERTAO": 5, 
    "GONCALO ALVES": 5, "PEQUI": 5, "MANGABA": 5, "CAGAITA": 5, "GUARIROBA": 5,
    "PALMITO AMARGO": 5,
    
    # Nomes Científicos
    "ASPIDOSPERMA POLYNEURON": 10, "CEDRELA FISSILIS": 10, "CEDRELA ODORATA": 10,
    "CARINIANA LEGALIS": 10, "MEZILAURUS ITAUBA": 10, "SCHINOPSIS BRASILIENSIS": 10,
    "MELANOXYLON BRAUNA": 10, "MYRACRODRUON URUNDEUVA": 5, "ASTRONIUM FRAXINIFOLIUM": 5,
    "HANCORNIA SPECIOSA": 5, "EUGENIA DYSENTERICA": 5, "SYAGRUS OLERACEA": 5
}

# --- 2. PARÂMETROS DE AUDITORIA BIOMÉTRICA ---

LIMITES_BIOMETRICOS = {
    "DAP_MIN_CM": 3.0,     # Abaixo disso, suspeita de erro ou regeneração
    "DAP_MAX_CM": 250.0,   # Árvore monumental (checar digitação)
    "ALTURA_MAX_M": 55.0,  # Árvore mais alta que prédio de 18 andares? Suspeito.
    "FATOR_ESBELTEZ_MIN": 0.4, 
    "FATOR_ESBELTEZ_MAX": 2.5  
}

# --- 3. MAPEAMENTO DE COLUNAS ---

SINONIMOS_COLUNAS = {
    "PARCELA": ["PARCELA", "TALHAO", "UNIDADE_AMOSTRAL", "P"],
    "ARVORE": ["ARVORE", "NUM_ARVORE", "N_ARVORE", "INDIVIDUO"],
    "NOME_COMUM": ["NOME_COMUM", "NOME_VULGAR", "ESPECIE_COMUM", "COMUM"],
    "NOME_CIENTIFICO": ["NOME_CIENTIFICO", "ESPECIE", "NOME_CIENT", "CIENTIFICO"],
    "DAP": ["DAP", "DAP(CM)", "DIAMETRO", "DBH"],
    "CAP": ["CAP", "CAP(CM)", "CIRCUNFERENCIA"],
    "ALTURA": ["ALTURA", "ALTURA_TOTAL", "HT", "H_TOTAL", "ALT", "ALT_TOT"],
    "ALTURA_COMERCIAL": ["ALTURA_COMERCIAL", "HC", "H_COM", "ALT_COM"]
}
