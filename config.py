"""
ARQUIVO DE CONFIGURAÇÃO - MUTUM
"""

# --- GERAL ---
APP_TITLE = "MUTUM 🛰️"
APP_VERSION = "3.0 (Siriema Layout)"

# --- SISTEMAS DE REFERÊNCIA ---
CRS_INTERNAL = "EPSG:4674"  # SIRGAS 2000
CRS_METRIC = "EPSG:31981"   # UTM 21S

# --- MAPA BASE (IMASUL/SIRIEMA) ---
MAP_CENTER_LAT = -20.4697
MAP_CENTER_LON = -54.6201
MAP_ZOOM_START = 12

# AQUI ESTÁ O TRUQUE: Dicionário de Mapas Base.
# Se você tiver o link WMS exato do Imasul (ArcGIS Server), substitua nas URLs abaixo.
# Por enquanto, coloquei imagens de satélite padrão e uma placeholder para 2008.
BASEMAPS = {
    "Satélite Atual (2024/25)": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attr": "Esri World Imagery",
        "name": "Satélite 2025"
    },
    "Google Hybrid (Referência)": {
        "url": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        "attr": "Google",
        "name": "Google Híbrido"
    },
    "Mapa de Ruas": {
        "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attr": "OSM",
        "name": "Ruas"
    }
    # Para adicionar a de 2008 do Imasul, você precisará da URL WMS/Tile correta.
    # Exemplo (hipotético):
    # "Ortofoto 2008": {
    #     "url": "https://gis.imasul.ms.gov.br/arcgis/rest/services/ORTOFOTOS_2008/MapServer/tile/{z}/{y}/{x}",
    #     "attr": "Imasul"
    # }
}

# --- DICIONÁRIO DE CLASSES (PORTARIA IMASUL 1.404) ---
CLASSES_MAPPING = {
    "PERIMETRO": {
        "keywords": ["imovel", "area_total", "perimetro", "gleba", "matricula", "101-poligono"],
        "label": "Área Total do Imóvel",
        "color": "#FF00FF",      # Magenta (Igual Siriema)
        "fill_color": "#FFFFFF",
        "weight": 3,
        "fillOpacity": 0.0,      # Transparente por padrão
        "z_index": 10
    },
    "NATIVA": {
        "keywords": ["remanescente", "vegetacao", "nativa", "reserva", "rl", "veg", "floresta"],
        "label": "Área de Remanescente de Vegetação Nativa",
        "color": "#228B22",      # ForestGreen
        "weight": 1,
        "fillOpacity": 0.5,
        "z_index": 5
    },
    "APP": {
        "keywords": ["app", "preservacao", "permanente", "ciliar", "nascente"],
        "label": "Área de Preservação Permanente (APP)",
        "color": "#32CD32",      # LimeGreen
        "weight": 1,
        "fillOpacity": 0.6,
        "z_index": 6
    },
    "CONSOLIDADA": {
        "keywords": ["uso", "consolidada", "antropizada", "pasto", "agricultura", "lavoura"],
        "label": "Área de Uso Consolidado",
        "color": "#000080",      # Navy Blue (Próximo do Siriema)
        "weight": 1,
        "fillOpacity": 0.5,
        "z_index": 4
    },
    "HIDROGRAFIA": {
        "keywords": ["rio", "lago", "represa", "agua", "curso"],
        "label": "Hidrografia",
        "color": "#00BFFF",      # DeepSkyBlue
        "weight": 1,
        "fillOpacity": 0.8,
        "z_index": 7
    },
    "SERVIDAO": {
        "keywords": ["servidao", "linha", "utilidade"],
        "label": "Servidão Administrativa",
        "color": "#808080",      # Gray
        "weight": 1,
        "fillOpacity": 0.5,
        "z_index": 8
    }
}

CLASS_DEFAULT = {
    "label": "Outros / Não Identificado",
    "color": "#800080",
    "weight": 1,
    "fillOpacity": 0.5,
    "z_index": 1
}
