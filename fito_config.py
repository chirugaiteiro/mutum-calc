# fito_config.py
# -*- coding: utf-8 -*-

"""
Arquivo de configuração para o Módulo de Inventário e Fitossociologia (Mutum).
Contém listas oficiais, parâmetros de validação e dicionários de mapeamento.
"""

# --- 1. LISTAS DE ESPÉCIES PROTEGIDAS E AMEAÇADAS ---

# Compensação Estadual (Resolução SEMADE n.9/2015 - Art. 52)
# Fonte: Baseada no código original do casual_simples.py
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

# Lista Vermelha MMA (Portarias 443/2014, 444/2014 e atualizações)
# Categorias: VU (Vulnerável), EN (Em Perigo), CR (Criticamente em Perigo)
# Amostra focada em espécies arbóreas comuns no Centro-Oeste/MS
LISTA_VERMELHA_MMA = {
    "ARAUCARIA ANGUSTIFOLIA": "EN", # Pinheiro-do-paraná
    "DICKSONIA SELLOWIANA": "EN",   # Xaxim
    "AMBURANA CEARENSIS": "EN",     # Cerejeira / Cumaru-de-cheiro
    "CEDRELA FISSILIS": "VU",       # Cedro
    "BERTHOLLETIA EXCELSA": "VU",   # Castanheira
    "SWIETENIA MACROPHYLLA": "VU",  # Mogno
    "TABEBUIA CASSINOIDES": "EN",   # Caixeta
    "OCOTEA POROSA": "VU",          # Imbuia
    "DALBERGIA NIGRA": "VU",        # Jacarandá-da-bahia
    "DIMORPHANDRA WILSONII": "CR"   # Faveiro-de-wilson
}

# --- 2. PARÂMETROS DE AUDITORIA BIOMÉTRICA (O "Guarda") ---

LIMITES_BIOMETRICOS = {
    "DAP_MIN_CM": 3.0,     # Abaixo disso, suspeita de erro ou regeneração não recrutada
    "DAP_MAX_CM": 250.0,   # Árvore monumental acima disso (checar digitação)
    "ALTURA_MAX_M": 55.0,  # Árvore mais alta que prédio de 18 andares? Suspeito.
    "FATOR_ESBELTEZ_MIN": 0.4, # H/DAP muito baixo (árvore "panqueca")
    "FATOR_ESBELTEZ_MAX": 2.5  # H/DAP muito alto (árvore "agulha") - Ex: 20m de altura e 5cm de DAP
}

# --- 3. MAPEAMENTO DE COLUNAS (Para aceitar variações do Excel) ---

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
