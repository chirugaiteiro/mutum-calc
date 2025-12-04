"""
ARQUIVO DE CONFIGURAÇÃO - MUTUM
Este arquivo centraliza todas as constantes, parâmetros e regras de negócio do sistema.
Alterar este arquivo modifica o comportamento do aplicativo sem necessidade de mexer no código-fonte.
"""

# --- GERAL ---
APP_TITLE = "MUTUM 🛰️"
APP_VERSION = "2.0 (Parametrized)"
UPLOAD_FOLDER = "temp_uploads"

# --- SISTEMAS DE REFERÊNCIA (CRS) ---
# O padrão oficial do Brasil é SIRGAS 2000.
# O sistema tentará converter tudo para CRS_INTERNAL para cálculos e visualização.
CRS_INTERNAL = "EPSG:4674"  # SIRGAS 2000 (Lat/Long) - Melhor para mapas web/Folium
CRS_METRIC = "EPSG:31981"   # SIRGAS 2000 / UTM zone 21S - Usado para cálculos precisos de área em MS (opcional)

# --- MAPA BASE (VISUALIZAÇÃO) ---
# Coordenadas centrais (focadas em MS/Campo Grande) para abertura inicial do mapa
MAP_CENTER_LAT = -20.4697
MAP_CENTER_LON = -54.6201
MAP_ZOOM_START = 6

# --- DICIONÁRIO DE CLASSES (PORTARIA IMASUL 1.404) ---
# A chave (ex: 'NATIVA') é usada internamente pelo código.
# 'keywords': Lista de palavras que o sistema busca no arquivo do usuário para adivinhar a classe.
# 'label': O nome bonito que vai aparecer na tabela e na legenda (conforme Portaria).
# 'color': Cor hexadecimal para o mapa (estilo Siriema).
# 'z_index': Ordem de plotagem (maior fica por cima).

CLASSES_MAPPING = {
"PERIMETRO": {
        # Adicionei "carms" e códigos comuns do siriema nas keywords
        "keywords": ["imovel", "area_total", "perimetro", "gleba", "matricula", "101-poligono"],
        "label": "Área Total do Imóvel",
        "color": "#000000",      # Borda Preta
        "fill_color": "#FFFFFF", # Cor irrelevante pois a opacidade será 0
        "opacity": 1.0,          # Opacidade da BORDA
        "fillOpacity": 0.0,      # <--- IMPORTANTE: Miolo 100% transparente
        "weight": 3,             # Borda mais grossa para destacar
        "z_index": 1
    },
    "NATIVA": {
        "keywords": ["remanescente", "vegetacao", "nativa", "reserva", "rl", "veg", "floresta", "mata", "cerrado"],
        "label": "Área de Remanescente de Vegetação Nativa",
        "color": "#228B22",      # ForestGreen (Verde Mata)
        "opacity": 0.6,
        "style": "polygon",
        "z_index": 2
    },
    "APP": {
        "keywords": ["app", "preservacao", "permanente", "ciliar", "nascente", "vereda", "borda"],
        "label": "Área de Preservação Permanente (APP)",
        "color": "#32CD32",      # LimeGreen (Verde Claro chamativo)
        "opacity": 0.7,
        "style": "polygon",
        "z_index": 3
    },
    "CONSOLIDADA": {
        "keywords": ["uso", "consolidada", "antropizada", "pasto", "agricultura", "lavoura", "cultura"],
        "label": "Área de Uso Consolidado / Antropizada",
        "color": "#F4A460",      # SandyBrown (Cor de terra/pasto seco)
        "opacity": 0.6,
        "style": "polygon",
        "z_index": 2
    },
    "HIDROGRAFIA": {
        "keywords": ["rio", "lago", "represa", "acude", "barragem", "agua", "curso"],
        "label": "Hidrografia / Corpos D'água",
        "color": "#1E90FF",      # DodgerBlue
        "opacity": 0.8,
        "style": "polygon",
        "z_index": 4
    },
    "SERVIDAO": {
        "keywords": ["servidao", "linha", "transmissao", "duto", "utilidade"],
        "label": "Área de Servidão Administrativa / Utilidade Pública",
        "color": "#808080",      # Gray
        "opacity": 0.5,
        "style": "polygon",
        "z_index": 5
    }
}

# Configuração de "Outros" para o que não for identificado
CLASS_DEFAULT = {
    "label": "Outros / Não Identificado",
    "color": "#800080", # Roxo (para destacar erro/falta de padrão)
    "opacity": 0.5
}
