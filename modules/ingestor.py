import streamlit as st
import geopandas as gpd
import pandas as pd
import tempfile
import os
import shutil
import fiona
from shapely.geometry import box
# Importa as configurações que acabamos de criar
import config

def save_and_extract(uploaded_file):
    """
    Salva o arquivo de upload em uma pasta temporária e extrai se for ZIP.
    Retorna o caminho do arquivo principal (.shp, .kml, etc).
    """
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, uploaded_file.name)
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Se for ZIP, extrai e procura shapefiles
    if uploaded_file.name.lower().endswith('.zip'):
        shutil.unpack_archive(file_path, temp_dir)
        
        # Procura recursivamente por arquivos espaciais suportados
        valid_extensions = ['.shp', '.kml', '.geojson', '.gpkg']
        found_files = []
        
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in valid_extensions):
                    found_files.append(os.path.join(root, file))
        
        if not found_files:
            raise ValueError("Nenhum arquivo geográfico (.shp, .kml, etc) encontrado dentro do ZIP.")
        
        return found_files # Retorna lista de arquivos encontrados
    
    return [file_path]

def enforce_crs(gdf):
    """
    Força a conversão para o CRS padrão definido no config (SIRGAS 2000).
    """
    target_crs = config.CRS_INTERNAL
    
    if gdf.crs is None:
        # Se não tiver CRS, assume SIRGAS 2000 (padrão Brasil) mas avisa
        # Em um sistema real, idealmente perguntaríamos ao usuário, mas aqui assumimos o padrão.
        gdf.set_crs(target_crs, inplace=True)
    else:
        gdf = gdf.to_crs(target_crs)
    
    return gdf

def identify_class(row, filename):
    """
    A MÁGICA: Tenta descobrir o que é a geometria baseada no config.py.
    Verifica tanto atributos (colunas) quanto o nome do arquivo de origem.
    """
    # 1. Tenta identificar pelo nome do arquivo (ex: 'app.shp')
    text_to_search = str(filename).lower()
    
    # 2. Se houver coluna de texto relevante, adiciona à busca
    # Procura colunas comuns como 'CLASSE', 'USO', 'TIPO', 'LAYER'
    possible_cols = ['classe', 'uso', 'tipo', 'layer', 'name', 'nome']
    cols_found = [c for c in gdf.columns if c.lower() in possible_cols]
    
    if cols_found:
        # Pega o valor da primeira coluna relevante encontrada
        val = str(row[cols_found[0]]).lower()
        text_to_search += " " + val

    # 3. Compara com o dicionário do config.py
    for class_key, rules in config.CLASSES_MAPPING.items():
        for keyword in rules['keywords']:
            if keyword in text_to_search:
                return class_key # Retorna a chave (ex: 'NATIVA')
    
    return "DEFAULT" # Se não achar nada

def calculate_metrics(gdf):
    """
    Calcula área em Hectares.
    Para precisão, reprojeta temporariamente para UTM ou projeção de área igual.
    """
    # Cria uma cópia reprojetada para UTM (métrica) apenas para calcular área
    # O EPSG 31981 é UTM 21S (comum em MS), mas para cobrir todo MS idealmente usaríamos Albers.
    # Para simplicidade e rapidez, UTM 21S resolve 90% dos casos no MS.
    gdf_metric = gdf.to_crs(config.CRS_METRIC)
    
    # Cálculo: Área em m² / 10000 = Hectares
    gdf['area_ha'] = gdf_metric.geometry.area / 10000
    gdf['area_ha'] = gdf['area_ha'].round(4) # Arredonda para 4 casas (padrão cartório)
    
    return gdf

def process_file(uploaded_file):
    """
    Função Principal chamada pelo App.
    Lê, padroniza, classifica e calcula.
    Retorna um GeoDataFrame único consolidado.
    """
    try:
        files = save_and_extract(uploaded_file)
        all_gdfs = []

        for file_path in files:
            # Suporte especial para KML (drivers)
            filename = os.path.basename(file_path)
            driver = 'KML' if filename.lower().endswith('.kml') else None
            
            if driver == 'KML':
                fiona.drvsupport.supported_drivers['KML'] = 'rw'
            
            try:
                gdf = gpd.read_file(file_path, driver=driver)
            except Exception as e:
                # Se falhar um arquivo do zip, pula ele mas tenta os outros
                continue

            # 1. Padronizar CRS
            gdf = enforce_crs(gdf)
            
            # 2. Calcular Área (Hectares)
            # Filtra apenas Polígonos para cálculo de área
            if not gdf.empty and gdf.geom_type.isin(['Polygon', 'MultiPolygon']).any():
                 gdf = calculate_metrics(gdf)
            else:
                 gdf['area_ha'] = 0.0

            # 3. Classificação Automática
            # Aplica a função identify_class linha a linha
            gdf['internal_class'] = gdf.apply(lambda row: identify_class(row, filename), axis=1)
            
            # Adiciona metadados visuais baseados na classe identificada
            gdf['label_oficial'] = gdf['internal_class'].apply(
                lambda k: config.CLASSES_MAPPING.get(k, config.CLASS_DEFAULT)['label']
            )
            gdf['color'] = gdf['internal_class'].apply(
                lambda k: config.CLASSES_MAPPING.get(k, config.CLASS_DEFAULT)['color']
            )
            
            all_gdfs.append(gdf)

        if not all_gdfs:
            return None, "Nenhum dado válido encontrado."

        # Junta tudo num único GeoDataFrame
        final_gdf = pd.concat(all_gdfs, ignore_index=True)
        return final_gdf, None

    except Exception as e:
        return None, str(e)
