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
text_to_search = str(filename).lower()
    
    # Normaliza o nome do arquivo (remove _ e - para facilitar match)
    text_to_search = text_to_search.replace("_", " ").replace("-", " ")

    # Tenta achar colunas descritivas na tabela de atributos
    possible_cols = ['classe', 'uso', 'tipo', 'layer', 'legenda', 'tema']
    # Interseção entre colunas existentes e possíveis
    valid_cols = [c for c in gdf_columns if c.lower() in possible_cols]
    
    if valid_cols:
        # Pega o valor da primeira coluna encontrada
        val = str(row[valid_cols[0]]).lower()
        text_to_search += " " + val

    # Compara com o dicionário do config
    for class_key, rules in config.CLASSES_MAPPING.items():
        for keyword in rules['keywords']:
            # Verifica se a keyword está no texto de busca
            if keyword in text_to_search:
                return class_key
    
    return "DEFAULT"

def process_file(uploaded_file):
    try:
        files = save_and_extract(uploaded_file)
        all_gdfs = []

        for file_path in files:
            filename = os.path.basename(file_path)
            
            # --- CORREÇÃO DE ENCODING ---
            # Tenta ler com UTF-8, se falhar, tenta CP1252 (comum no Brasil/ArcGIS)
            try:
                gdf = gpd.read_file(file_path, encoding='utf-8')
            except:
                try:
                    gdf = gpd.read_file(file_path, encoding='cp1252')
                except Exception as e:
                    # Se falhar kml ou drivers exóticos
                    if file_path.endswith('.kml'):
                        fiona.drvsupport.supported_drivers['KML'] = 'rw'
                        gdf = gpd.read_file(file_path, driver='KML')
                    else:
                        continue # Pula arquivo corrompido

            # 1. Padronizar CRS
            gdf = enforce_crs(gdf)
            
            # 2. Calcular Área
            if not gdf.empty and gdf.geom_type.isin(['Polygon', 'MultiPolygon']).any():
                 gdf = calculate_metrics(gdf)
            else:
                 gdf['area_ha'] = 0.0

            # 3. Classificação Automática (passando colunas agora)
            gdf['internal_class'] = gdf.apply(lambda row: identify_class(row, filename, gdf.columns), axis=1)
            
            # Mapeamento visual
            gdf['label_oficial'] = gdf['internal_class'].apply(
                lambda k: config.CLASSES_MAPPING.get(k, config.CLASS_DEFAULT)['label']
            )
            gdf['color'] = gdf['internal_class'].apply(
                lambda k: config.CLASSES_MAPPING.get(k, config.CLASS_DEFAULT)['color']
            )
            
            # --- CORREÇÃO VISUAL PARA PERÍMETRO ---
            # Se for perimetro, zera o fillOpacity, senão usa padrão
            gdf['fillOpacity'] = gdf['internal_class'].apply(
                lambda k: config.CLASSES_MAPPING.get(k, {}).get('fillOpacity', 0.6)
            )
            gdf['weight'] = gdf['internal_class'].apply(
                lambda k: config.CLASSES_MAPPING.get(k, {}).get('weight', 1)
            )

            all_gdfs.append(gdf)

        if not all_gdfs:
            return None, "Nenhum dado válido encontrado."

        final_gdf = pd.concat(all_gdfs, ignore_index=True)
        return final_gdf, None

    except Exception as e:
        return None, str(e)
