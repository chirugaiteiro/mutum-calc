# fito_config.py
# -*- coding: utf-8 -*-

"""
Arquivo de configuração para o Módulo de Inventário e Fitossociologia (Mutum).
Contém listas oficiais, parâmetros de validação e dicionários de mapeamento.
"""

# --- 1. LISTAS DE ESPÉCIES (URLs e Dicionários Fixos) ---

# URL "Raw" para leitura do CSV no GitHub
URL_LISTA_MMA_CSV = "https://raw.githubusercontent.com/chirugaiteiro/bases_ambientais/main/flora-ameacada-2021.csv"

# Compensação Estadual (Resolução SEMADE n.9/2015 - Art. 52)
# ATUALIZADO com a lista completa do seu código original
LISTA_IMASUL_COMPENSACAO = {
    # Nomes Comuns
    "PEROBA ROSA": 10, "CEDRO": 10, "CEDRO ROSA": 10, "JEQUITIBA": 10, 
    "ITAUBA": 10, "BARAUNA": 10, "QUEBRACHO": 10, "AROEIRA DO SERTAO": 5, 
    "GONCALO ALVES": 5, "PEQUI": 5, "MANGABA": 5, "CAGAITA": 5, "GUARIROBA": 5,
    "PALMITO AMARGO": 5, "AROEIRA": 5, "ACURI": 0, "BOCAIUVA": 0, # Adicionei comuns extras
    
    # Nomes Científicos (Do seu código original)
    "ASPIDOSPERMA POLYNEURON": 10, "CEDRELA FISSILIS": 10, "CEDRELA ODORATA": 10,
    "CARINIANA LEGALIS": 10, "MEZILAURUS ITAUBA": 10, "SCHINOPSIS BRASILIENSIS": 10,
    "MELANOXYLON BRAUNA": 10, "MYRACRODRUON URUNDEUVA": 5, "ASTRONIUM FRAXINIFOLIUM": 5,
    "HANCORNIA SPECIOSA": 5, "EUGENIA DYSENTERICA": 5, "SYAGRUS OLERACEA": 5,
    "EUGENIA DYSENTERICA DC.": 5 # Variação comum
}

# --- 2. PARÂMETROS DE AUDITORIA BIOMÉTRICA ---

LIMITES_BIOMETRICOS = {
    "DAP_MIN_CM": 3.0,     # Abaixo disso, suspeita de erro ou regeneração
    "DAP_MAX_CM": 250.0,   # Árvore monumental
    "ALTURA_MAX_M": 55.0,  # Altura suspeita
    "FATOR_ESBELTEZ_MIN": 0.4, 
    "FATOR_ESBELTEZ_MAX": 2.5  
}

# --- 3. MAPEAMENTO DE COLUNAS ---

SINONIMOS_COLUNAS = {
    "PARCELA": ["PARCELA", "TALHAO", "UNIDADE_AMOSTRAL", "P"],
    "ARVORE": ["ARVORE", "NUM_ARVORE", "N_ARVORE", "INDIVIDUO", "NUM. ARVORE", "NUM. FUSTE"],
    "NOME_COMUM": ["NOME_COMUM", "NOME_VULGAR", "ESPECIE_COMUM", "COMUM", "NOME COMUM"],
    "NOME_CIENTIFICO": ["NOME_CIENTIFICO", "ESPECIE", "NOME_CIENT", "CIENTIFICO", "NOME CIENTIFICO"],
    "FAMILIA": ["FAMILIA", "FAMILY"],
    "DAP": ["DAP", "DAP(CM)", "DIAMETRO", "DBH"],
    "CAP": ["CAP", "CAP(CM)", "CIRCUNFERENCIA"],
    "ALTURA": ["ALTURA", "ALTURA_TOTAL", "HT", "H_TOTAL", "ALT", "ALT_TOT", "ALT. TOTAL"],
    "ALTURA_COMERCIAL": ["ALTURA_COMERCIAL", "HC", "H_COM", "ALT_COM", "ALT. COMERCIAL"]
}
