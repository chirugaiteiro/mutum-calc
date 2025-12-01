import streamlit as st
import geopandas as gpd
import requests
import json
import tempfile
import os
import zipfile
import datetime
import random
import concurrent.futures
from shapely.geometry import shape, Polygon, LineString, MultiLineString
from shapely.ops import unary_union
import folium
from streamlit_folium import st_folium
import urllib3
import pandas as pd

# Suprime avisos de SSL (necessário para servidores gov.br)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- IMPORTAÇÕES PARA O PLOT ESTÁTICO ---
import matplotlib.pyplot as plt
from PIL import Image
from io import BytesIO
import matplotlib.patheffects as pe

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="M.U.T.U.M. - MS", page_icon="🐦", layout="wide")

# --- DICIONÁRIO DE CLASSES (PORTARIA IMASUL 1404/2024) ---
# Mapeamento dos códigos numéricos do Siriema para descrições legíveis
DICIONARIO_CLASSES_SIRIEMA = {
    101: "Área Total do Imóvel",
    102: "Área Certificada pelo INCRA",
    103: "Remanescente de Vegetação Nativa",
    104: "Ocupação Agrosilvipastoril (Pré-2008)",
    105: "Ocupação por Outras Atividades",
    106: "Ocupação Agrosilvipastoril (Pós-2008)",
    113: "Área de Pousio",
    114: "Pastagem Nativa",
    115: "Sede do Imóvel",
    122: "Curso D'água (10-50m)",
    123: "Curso D'água (50-200m)",
    126: "Lago/Lagoa Natural",
    127: "Reservatório Artificial (Barramento)",
    129: "Nascente/Olho D'água",
    130: "Encosta > 45º",
    134: "Vereda",
    142: "Reserva Legal Aprovada/Averbada",
    143: "Reserva Legal em Condomínio",
    144: "Cota de Reserva Ambiental (CRA)",
    145: "Perímetro de Matrícula Individualizada",
    146: "Veg. Nativa para Compensação/TAC",
    150: "APP (Legislação Estadual/Municipal)",
    151: "Área Suprimida/A Suprimir",
    152: "Terra Indígena",
    153: "Área Quilombola",
    154: "Unidade de Conservação",
    155: "Área Embargada",
    156: "Área Úmida Brejosa",
    157: "Área Úmida Campo de Inundação",
    160: "Área Prioritária Banhados",
    173: "Informativo de PRADE"
}

# --- LISTAS DE BASES (MANTIDAS) ---
BASES_GERAIS = [
    {"nome": "Unidades de Conservação", "url": "https://www.pinms.ms.gov.br/arcgis/rest/services/IMASUL/UCs_MS_Mosaico/MapServer/0/query", "colunas_nome": ["Nome UC", "NOME_UC", "NM_UC"], "coluna_legis": ["leis", "LEIS"], "tipo": "poligono"},
    {"nome": "Terras Indígenas", "url": "https://www.pinms.ms.gov.br/arcgis/rest/services/IMASUL/CAMADAS_API_SISGEO_v1/FeatureServer/4/query", "colunas_nome": ["terrai_nom", "TERRAI_NOM"], "coluna_legis": ["fase_ti"], "tipo": "poligono"},
    {"nome": "Povos Tradicionais (Quilombolas)", "url": "https://www.pinms.ms.gov.br/arcgis/rest/services/AGRAER_SERVICOS/Povos_Tradicionais/MapServer/2/query", "colunas_nome": ["nm_comunid", "NM_COMUNID"], "coluna_legis": ["ob_descric"], "tipo": "poligono"},
    {"nome": "Áreas de Uso Restrito (Dec. 15.661)", "url": "https://www.pinms.ms.gov.br/arcgis/rest/services/IMASUL/SiriemaGeo_Sisla/MapServer/49/query", "colunas_nome": ["TOPONIMIA", "toponimia"], "coluna_legis": ["CLASSE"], "tipo": "poligono"},
    {"nome": "Áreas Priorit. Banhados", "url": "https://www.pinms.ms.gov.br/arcgis/rest/services/IMASUL/SiriemaGeo_Sisla/MapServer/52/query", "colunas_nome": ["CLASSE", "classe"], "coluna_legis": ["leis"], "tipo": "poligono"},
    {"nome": "Corredores Ecológicos do Pantanal", "url": "https://www.pinms.ms.gov.br/arcgis/rest/services/IMASUL/Corredores_Ecológicos_Pantanal/MapServer/0/query", "colunas_nome": ["corredor", "CORREDOR", "nome"], "coluna_legis": ["leis"], "tipo": "poligono"},
    {"nome": "Área de Entorno 0-3 Km (Rio Taquari)", "url": "https://www.pinms.ms.gov.br/arcgis/rest/services/IMASUL/SiriemaGeo_Sisla/MapServer/48/query", "colunas_nome": ["FID", "gid"], "coluna_legis": [], "tipo": "poligono"},
    {"nome": "Zona de Amortecimento (Estaduais)", "url": "https://www.pinms.ms.gov.br/arcgis/rest/services/IMASUL/CAMADAS_API_SISGEO_v1/FeatureServer/2/query", "colunas_nome": ["NOME_UC", "nome_uc"], "coluna_legis": ["leis"], "tipo": "poligono"},
    {"nome": "ZA (Conama 0-2km)", "url": "https://www.pinms.ms.gov.br/arcgis/rest/services/IMASUL/CAMADAS_API_SISGEO_v1/FeatureServer/1/query", "colunas_nome": ["NOME", "nome"], "coluna_legis": ["FAIXA"], "tipo": "poligono"},
    {"nome": "ZA (Conama 0-3km)", "url": "https://www.pinms.ms.gov.br/arcgis/rest/services/IMASUL/CAMADAS_API_SISGEO_v1/FeatureServer/0/query", "colunas_nome": ["NOME", "nome"], "coluna_legis": ["FAIXA"], "tipo": "poligono"},
    {"nome": "Biomas MS", "url": "https://www.pinms.ms.gov.br/arcgis/rest/services/IMASUL/lim_biomas_atual/MapServer/0/query", "colunas_nome": ["nm_bioma", "Bioma"], "coluna_legis": ["info_legis"], "tipo": "ponto"}
]

BASES_HIDRO = [
    {"nome": "Hidrografia MS (Rios)", "url": "https://www.pinms.ms.gov.br/arcgis/rest/services/SEMADESC/SEMADESC_MAPAS/MapServer/12/query", "colunas_nome": ["NOME", "nome", "Nome"], "coluna_legis": ["REGIME", "regime"], "tipo": "linha"}
]

BASES_FISCALIZACAO = [
    {"nome": "Embargos IBAMA", "tipo_fonte": "REST", "url": "https://pamgia.ibama.gov.br/server/rest/services/01_Publicacoes_Bases/adm_embargos_ibama_a/MapServer/0/query", "colunas_nome": ["num_tad", "NUM_TAD"], "tipo": "poligono"},
    {"nome": "Embargos ICMBio", "tipo_fonte": "WFS", "url": "https://geoservicos.inde.gov.br/geoserver/ICMBio/ows", "layer_name": "ICMBio:embargos_icmbio", "colunas_nome": ["numero_embargo", "numero_emb"], "tipo": "poligono"},
    {"nome": "MapBiomas Alerta", "tipo_fonte": "WFS", "url": "https://production.alerta.mapbiomas.org/geoserver/wfs", "layer_name": "mapbiomas-alertas:alert_report", "colunas_nome": ["alert_code", "alerta_id"], "tipo": "poligono"},
    {"nome": "Focos de Calor (INPE - Ano Atual)", "tipo_fonte": "WFS", "url": "https://queimadas.dgi.inpe.br/queimadas/geoserver/wfs", "layer_name": "bdqueimadas:focos_br_ref", "colunas_nome": ["data_pas", "satelite"], "tipo": "ponto"}
]

BASES_LICENCAS = [
    {"nome": "Licenças Emitidas (Siriema/IMASUL)", "url": "https://www.pinms.ms.gov.br/arcgis/rest/services/IMASUL/licencas_ambientais/FeatureServer/16/query", "colunas_nome": ["num_processo", "processo", "n_processo", "emp_id"], "coluna_legis": ["atividade", "desc_ativ", "tipologia"], "tipo": "poligono"}
]

# --- URLS ---
URL_DECLIVIDADE_EXPORT = "https://www.pinms.ms.gov.br/arcgis/rest/services/Imagens/fusao_declividade_graus/ImageServer/exportImage"
URL_HIDRO_EXPORT = "https://www.pinms.ms.gov.br/arcgis/rest/services/SEMADESC/SEMADESC_MAPAS/MapServer/export"

# --- FUNÇÕES AUXILIARES (MANTIDAS) ---
def gerar_cor_aleatoria():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

def buscar_valor_inteligente(attrs, lista_tentativas):
    if not attrs: return "N/D"
    attrs_lower = {k.lower(): v for k, v in attrs.items()}
    for chave in lista_tentativas:
        chave_low = chave.lower()
        if chave_low in attrs_lower and attrs_lower[chave_low]:
            val = attrs_lower[chave_low]
            if isinstance(val, (int, float)) and val > 100000000000:
                try: return datetime.datetime.fromtimestamp(val/1000).strftime('%d/%m/%Y')
                except: return str(val)
            return str(val)
    for key, val in attrs_lower.items():
        if ('nome' in key or 'nm_' in key) and val: return str(val)
    return "Não identificado"

def parse_float_br(valor_str):
    try:
        if isinstance(valor_str, (int, float)): return float(valor_str)
        return float(valor_str.replace('.', '').replace(',', '.'))
    except: return 0.0

def consultar_api_imasul(url, geometry_json, geometry_type):
    params = {'f': 'json', 'geometry': geometry_json, 'geometryType': geometry_type, 'spatialRel': 'esriSpatialRelIntersects', 'outFields': '*', 'returnGeometry': 'true', 'outSR': '31981'}
    try:
        response = requests.post(url, data=params, timeout=25)
        return response.json()
    except: return None

def consultar_wfs_icmbio(url, layer_name, bbox_list):
    bbox_str = f"{bbox_list[0]},{bbox_list[1]},{bbox_list[2]},{bbox_list[3]}"
    params = {"service": "WFS", "version": "1.0.0", "request": "GetFeature", "typeName": layer_name, "outputFormat": "application/json", "srsName": "EPSG:4674", "bbox": f"{bbox_str},EPSG:4674"}
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200: return response.json()
        else: return None
    except: return None

def processar_uma_base(base, dados_imovel):
    # (Função de processamento de sobreposição mantida)
    resultados_parcial = []
    camadas_parcial = []
    geom_utm_imovel = dados_imovel['geom_utm']
    area_imovel = dados_imovel['area_ha']
    
    resp = None
    if base.get('tipo_fonte') == 'WFS':
        resp = consultar_wfs_icmbio(base['url'], base['layer_name'], dados_imovel['bounds_4674'])
    else:
        if base['tipo'] == 'ponto': payload = dados_imovel['json_point']; gtype = 'esriGeometryPoint'
        else: payload = dados_imovel['json_poly']; gtype = 'esriGeometryPolygon'
        resp = consultar_api_imasul(base['url'], payload, gtype)
    
    if resp and 'features' in resp and len(resp['features']) > 0:
        for feat in resp['features']:
            attrs = feat.get('attributes') or feat.get('properties')
            nome = buscar_valor_inteligente(attrs, base['colunas_nome'])
            if not nome or nome == "N/D": nome = "Não identificado"
            legis = "-"
            detalhes_extras = {}
            
            # Extração de Metadados
            if "Licenças" in base['nome']:
                detalhes_extras['Processo'] = buscar_valor_inteligente(attrs, ["num_processo", "processo"])
                detalhes_extras['Atividade'] = buscar_valor_inteligente(attrs, ["atividade", "desc_ativ", "tipologia"])
                detalhes_extras['Tipo Licença'] = buscar_valor_inteligente(attrs, ["tipo_empre", "tipo_licenca", "desc_tiple"])
                detalhes_extras['Situacao'] = buscar_valor_inteligente(attrs, ["situacao", "status"])
                detalhes_extras['Vencimento'] = buscar_valor_inteligente(attrs, ["vencimento", "data_venc", "validade"])
            elif "Hidrografia" in base['nome']:
                detalhes_extras['Regime'] = buscar_valor_inteligente(attrs, ["REGIME", "regime"])
            elif "IBAMA" in base['nome']:
                detalhes_extras['Autuado'] = buscar_valor_inteligente(attrs, ["nome_embargado", "nom_pessoa", "nome_e"])
                detalhes_extras['CPF/CNPJ'] = buscar_valor_inteligente(attrs, ["cpf_cnpj", "CPF_CNPJ"])
                detalhes_extras['Data'] = buscar_valor_inteligente(attrs, ["dat_embargo", "dat_emb", "DAT_TAD"])
                detalhes_extras['Infração'] = buscar_valor_inteligente(attrs, ["des_infracao", "des_infra"])
            elif "ICMBio" in base['nome']:
                detalhes_extras['Autuado'] = buscar_valor_inteligente(attrs, ["autuado", "AUTUADO"])
                detalhes_extras['Data'] = buscar_valor_inteligente(attrs, ["data_tad", "DATA"])
            elif "MapBiomas" in base['nome']:
                detalhes_extras['Data Detecção'] = buscar_valor_inteligente(attrs, ["detected_at", "data_deteccao"])
                detalhes_extras['Bioma'] = buscar_valor_inteligente(attrs, ["biome", "bioma"])
            elif "Focos de Calor" in base['nome']:
                detalhes_extras['Satélite'] = buscar_valor_inteligente(attrs, ["satelite"])
                detalhes_extras['Data Hora'] = buscar_valor_inteligente(attrs, ["data_pas", "data_hora"])
            elif base.get('coluna_legis'):
                legis = buscar_valor_inteligente(attrs, base['coluna_legis'])
            
            area_txt, pct_txt = "---", "---"
            poly_base = None
            
            try:
                if base['tipo'] == 'ponto':
                    poly_base = shape(feat['geometry'])
                    area_txt = "Ponto no Imóvel"; pct_txt = "Foco/Ponto"
                elif base['tipo'] == 'linha':
                    poly_base = None
                    if 'geometry' in feat and 'paths' in feat['geometry']:
                         area_txt = "Sim"; pct_txt = "Cruzamento"
                else:
                    if base.get('tipo_fonte') == 'WFS': poly_base = shape(feat['geometry'])
                    elif 'geometry' in feat and 'rings' in feat['geometry']:
                        partes = [Polygon(a) for a in feat['geometry']['rings']]
                        poly_base = unary_union(partes)
            except: poly_base = None

            if base['tipo'] == 'linha' and area_txt == "Sim":
                 resultados_parcial.append({"Base": base['nome'], "Identificação": nome, "Detalhes": legis, "Área (ha)": "Trecho Detectado", "Status": "Verificar APP", "Extra": detalhes_extras})
            elif poly_base:
                try:
                    if not poly_base.is_valid: poly_base = poly_base.buffer(0)
                    interseccao = None
                    if base.get('tipo_fonte') == 'WFS':
                        aux_gdf = gpd.GeoDataFrame({'geometry': [poly_base]}, crs="EPSG:4674").to_crs(dados_imovel['crs_utm'])
                        interseccao = geom_utm_imovel.intersection(aux_gdf.geometry.iloc[0])
                    else:
                        interseccao = geom_utm_imovel.intersection(poly_base)

                    if not interseccao.is_empty:
                        area_calc = 0
                        if base['tipo'] == 'poligono':
                            area_calc = interseccao.area / 10000
                            if area_calc < 0.5: continue # Filtro Anti-Vizinho
                            area_txt = f"{area_calc:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            pct_txt = f"{(area_calc/area_imovel)*100:.2f}%"
                        
                        gdf_conf = gpd.GeoDataFrame({'geometry': [interseccao]}, crs=dados_imovel['crs_utm'])
                        nome_camada = f"{base['nome']}: {nome}"
                        geojson_str = gdf_conf.to_crs(epsg=4326).to_json()
                        cor_atual = gerar_cor_aleatoria()
                        camadas_parcial.append({"nome": nome_camada, "geojson": json.loads(geojson_str), "tipo": base['tipo'], "cor": cor_atual})
                        resultados_parcial.append({"Base": base['nome'], "Identificação": nome, "Detalhes": legis, "Área (ha)": area_txt, "Status": pct_txt, "Extra": detalhes_extras})
                except: pass
                
    return resultados_parcial, camadas_parcial

def executar_varredura_paralela(lista_bases, dados_imovel):
    todos_resultados = []
    todas_camadas = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_to_base = {executor.submit(processar_uma_base, base, dados_imovel): base for base in lista_bases}
        for future in concurrent.futures.as_completed(future_to_base):
            try:
                res, cam = future.result()
                todos_resultados.extend(res)
                todas_camadas.extend(cam)
            except: pass
    return todos_resultados, todas_camadas

def plotar_declividade_estatica(gdf_web):
    # (Funções de Plotagem Estática Mantidas)
    bounds = gdf_web.total_bounds
    margem = 0.005
    minx, miny, maxx, maxy = bounds[0]-margem, bounds[1]-margem, bounds[2]+margem, bounds[3]+margem
    bbox_str = f"{minx},{miny},{maxx},{maxy}"
    params = {"bbox": bbox_str, "bboxSR": "4326", "size": "1500,1500", "imageSR": "4326", "format": "png32", "pixelType": "U8", "noData": "", "interpolation": "RSP_BilinearInterpolation", "f": "image"}
    try:
        resp = requests.get(URL_DECLIVIDADE_EXPORT, params=params, timeout=25)
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content))
            fig, ax = plt.subplots(figsize=(12, 12))
            ax.imshow(img, extent=[minx, maxx, miny, maxy], aspect='auto')
            gdf_web.plot(ax=ax, facecolor='none', edgecolor='yellow', linewidth=3, path_effects=[pe.Stroke(linewidth=5, foreground='black'), pe.Normal()])
            ax.set_aspect('equal'); ax.set_axis_off(); ax.set_title("Carta de Declividade do Imóvel", fontsize=16, color='white', pad=20)
            fig.patch.set_facecolor('#0E1117')
            return fig
    except: return None
    return None

def plotar_hidrografia_imasul_estatica(gdf_web):
    # (Funções de Plotagem Estática Mantidas)
    bounds = gdf_web.total_bounds
    margem = 0.02
    minx, miny, maxx, maxy = bounds[0]-margem, bounds[1]-margem, bounds[2]+margem, bounds[3]+margem
    params = {"bbox": f"{minx},{miny},{maxx},{maxy}", "bboxSR": "4326", "layers": "show:12", "size": "1200,1200", "imageSR": "4326", "format": "png", "f": "image", "transparent": "false"}
    try:
        resp = requests.get(URL_HIDRO_EXPORT, params=params, timeout=30)
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content))
            fig, ax = plt.subplots(figsize=(12, 12))
            ax.imshow(img, extent=[minx, maxx, miny, maxy], aspect='auto')
            gdf_web.plot(ax=ax, facecolor='none', edgecolor='red', linewidth=2, path_effects=[pe.Stroke(linewidth=4, foreground='white'), pe.Normal()])
            ax.set_aspect('equal'); ax.set_axis_off(); ax.set_title("Hidrografia Oficial (SEMADESC)", fontsize=16, color='black', pad=20)
            fig.patch.set_facecolor('white')
            return fig
    except: return None
    return None

# --- FUNÇÃO DE LEITURA (AGORA COM VARREDURA RECURSIVA) ---
@st.cache_data(show_spinner=False)
def ler_arquivo_zip(file_bytes):
    """Lê o ZIP, faz varredura completa por .shp e retorna o GeoDataFrame bruto para seleção."""
    temp_dir = tempfile.mkdtemp()
    path_zip = os.path.join(temp_dir, "temp.zip")
    
    with open(path_zip, "wb") as f: f.write(file_bytes)
    
    try:
        with zipfile.ZipFile(path_zip, 'r') as zip_ref: zip_ref.extractall(temp_dir)
    except Exception as e:
        return None, f"Erro ao descompactar o ZIP: {str(e)}"

    # --- NOVA VARREDURA RECURSIVA (os.walk) ---
    caminhos_shp = []
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if file.lower().endswith('.shp'):
                caminhos_shp.append(os.path.join(root, file))
    
    if not caminhos_shp:
        return None, "Nenhum arquivo .shp encontrado no ZIP (verificação completa)."
        
    # Assume o primeiro .shp encontrado
    caminho_shp_final = caminhos_shp[0]
    
    try:
        gdf = gpd.read_file(caminho_shp_final)
        # Filtra apenas polígonos
        gdf = gdf[gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])]
        if gdf.empty: return None, "O arquivo .shp encontrado não contém polígonos."
        return gdf, None
    except Exception as e: 
        return None, f"Erro ao ler o shapefile: {str(e)}"

# --- FUNÇÃO DE PROCESSAMENTO FINAL (MANTIDA) ---
def processar_geometria_selecionada(gdf_selecionado, epsg_codigo):
    try:
        if not gdf_selecionado.crs:
            gdf_selecionado.set_crs(epsg=epsg_codigo, inplace=True)
        else:
            gdf_selecionado = gdf_selecionado.to_crs(epsg=epsg_codigo)
            
        geom_utm = gdf_selecionado.geometry.iloc[0]
        area_ha = geom_utm.area / 10000
        gdf_geo = gdf_selecionado.to_crs(epsg=4674)
        geom_geo = gdf_geo.geometry.iloc[0]
        json_poly = json.dumps({"rings": [list(geom_geo.exterior.coords)], "spatialReference": {"wkid": 4674}})
        ponto = geom_geo.centroid
        json_point = json.dumps({"x": ponto.x, "y": ponto.y, "spatialReference": {"wkid": 4674}})
        gdf_folium = gdf_selecionado.to_crs(epsg=4326)
        geojson_folium = gdf_folium.to_json()
        bounds = gdf_folium.total_bounds.tolist()
        centro = [ponto.y, ponto.x]
        bounds_4674 = gdf_geo.total_bounds.tolist()
        
        return {
            "geom_utm": geom_utm, "json_poly": json_poly, "json_point": json_point,
            "area_ha": area_ha, "geojson_folium": geojson_folium, "gdf_web": gdf_folium,
            "bounds": bounds, "bounds_4674": bounds_4674, "centro": centro, "crs_utm": gdf_selecionado.crs
        }
    except Exception as e: return None

# --- INTERFACE PRINCIPAL ---
st.title("🐦 M.U.T.U.M. - Vigilante Ambiental")
st.markdown("##### Ferramenta de Monitoramento Unificado de Terras e Uso em MS")

with st.expander("⚠️ AVISO LEGAL - VERSÃO BETA 4.1", expanded=True):
    st.warning("**ATENÇÃO:** Esta versão (BETA 4.1) agora faz uma **varredura completa** em subpastas dentro do ZIP, resolvendo o problema de uploads do Siriema/CAR.")

uploaded_file = st.file_uploader("📂 Arraste o arquivo ZIP do CAR/Siriema", type="zip")

if 'arquivo_atual' not in st.session_state or st.session_state['arquivo_atual'] != uploaded_file:
    st.session_state.clear()
    st.session_state['arquivo_atual'] = uploaded_file

if uploaded_file:
    # 1. Leitura Inicial
    if 'gdf_bruto' not in st.session_state:
        with st.spinner("Lendo arquivo do Siriema (Varredura de subpastas)..."):
            gdf, erro = ler_arquivo_zip(uploaded_file.getvalue())
            if erro: st.error(erro)
            else: st.session_state['gdf_bruto'] = gdf

    if 'gdf_bruto' in st.session_state:
        gdf = st.session_state['gdf_bruto']
        
        # 2. Configuração de Projeção
        st.write("---")
        st.subheader("1. Configuração de Projeção")
        
        crs_opcoes = {"SIRGAS 2000 / UTM 21S (EPSG:31981)": 31981, "SIRGAS 2000 / UTM 22S (EPSG:31982)": 31982}
        epsg_escolhido = None
        
        if gdf.crs:
            st.success(f"Projeção detectada: {gdf.crs}")
            epsg_escolhido = gdf.crs.to_epsg()
            if epsg_escolhido not in [31981, 31982, 4674, 4326]: # Adicionando 4674 e 4326 para evitar aviso falso
               st.warning(f"A projeção detectada ({epsg_escolhido}) não é UTM 21S nem 22S. O cálculo de área pode variar. Vamos reprojetar para 21S para continuar.")
               # Força a reprojeção para 21S se a detectada for "estranha"
               epsg_escolhido = 31981 
        else:
            st.warning("⚠️ O arquivo não possui definição de projeção (.prj). Por favor, informe o fuso UTM correto:")
            epsg_label = st.radio("Selecione o Fuso UTM:", list(crs_opcoes.keys()))
            epsg_escolhido = crs_opcoes[epsg_label]

        # 3. Seleção do Polígono
        st.write("---")
        st.subheader("2. Seleção da Geometria para Análise")
        
        opcoes_poligonos = {}
        indice_padrao_idx = 0
        
        # Processa as linhas do GDF para criar as opções do Seletor
        for i, row in gdf.reset_index(drop=True).iterrows():
            nome_classe = "Polígono sem Classe"
            area_pol = row.geometry.to_crs(epsg=31981).area / 10000 if gdf.crs else 0.0
            
            if 'CLASSE' in gdf.columns:
                cod_classe = row['CLASSE']
                if pd.notnull(cod_classe):
                    try:
                        cod_int = int(cod_classe)
                        descricao = DICIONARIO_CLASSES_SIRIEMA.get(cod_int, f"Classe Desconhecida ({cod_int})")
                        nome_classe = f"[{cod_int}] {descricao}"
                        if cod_int == 101: indice_padrao_idx = i # Define Área Total como padrão
                    except:
                        nome_classe = f"Classe Inválida: {cod_classe}"
            
            label = f"ID {i}: {nome_classe} (aprox. {area_pol:.2f} ha)"
            opcoes_poligonos[label] = i
        
        # Garante que as opções existam antes de usar selectbox
        if not opcoes_poligonos:
            st.error("Nenhum polígono válido encontrado para seleção.")
        else:
            label_selecionado = st.selectbox(
                "Qual polígono será o objeto da varredura?", 
                list(opcoes_poligonos.keys()),
                index=indice_padrao_idx if indice_padrao_idx < len(opcoes_poligonos) else 0
            )
            
            idx_escolhido = opcoes_poligonos[label_selecionado]
            
            if st.button("✅ Confirmar Geometria e Iniciar Análise", type="primary"):
                if not epsg_escolhido:
                    st.error("Por favor, selecione o Fuso UTM antes de confirmar.")
                else:
                    gdf_selecionado = gdf.iloc[[idx_escolhido]].copy()
                    
                    dados_geo = processar_geometria_selecionada(gdf_selecionado, epsg_escolhido)
                    
                    if dados_geo:
                        st.session_state['dados_geo'] = dados_geo
                        st.session_state['analise_confirmada'] = True
                        st.rerun()

    # --- TELA DE ANÁLISE (SÓ APARECE DEPOIS DE CONFIRMAR) ---
    if st.session_state.get('analise_confirmada') and 'dados_geo' in st.session_state:
        dados_geo = st.session_state['dados_geo']
        st.write("---")
        st.info(f"📍 **Analisando Geometria:** {dados_geo['area_ha']:,.4f} ha")
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 1. Restrições", "⛰️ 2. Declividade", "💧 3. Hidrografia", "🔥 4. Fiscalização/Calor", "🍒 5. Licenciamento"])

        # O restante do código de execução das abas (1 a 5) foi mantido intacto.

        with tab1:
            st.markdown("### Monitoramento de Restrições Gerais")
            if st.button("🦅 Levantar Voo (Iniciar Varredura Rápida)", type="primary", use_container_width=True):
                with st.spinner("🐦 Sobrevoando todas as bases simultaneamente..."):
                    res, mapa = executar_varredura_paralela(BASES_GERAIS, dados_geo)
                    st.session_state['resultados_geral'] = res
                    st.session_state['mapa_geral'] = mapa
                    st.session_state['fase_geral_feita'] = True
            if st.session_state.get('fase_geral_feita'):
                if st.session_state['resultados_geral']:
                    st.error(f"⚠️ O Mutum avistou **{len(st.session_state['resultados_geral'])}** sobreposições.")
                    df_show = [{k:v for k,v in r.items() if k!='Extra' and k!='Status'} for r in st.session_state['resultados_geral']]
                    st.dataframe(df_show, use_container_width=True)
                else: st.success("✅ Horizonte limpo!")
                m1 = folium.Map(location=dados_geo['centro'], zoom_start=12)
                m1.fit_bounds([[dados_geo['bounds'][1], dados_geo['bounds'][0]], [dados_geo['bounds'][3], dados_geo['bounds'][2]]])
                folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m1)
                folium.GeoJson(dados_geo['geojson_folium'], style_function=lambda x: {'fillColor': '#ffff00', 'color': 'yellow', 'fillOpacity': 0.1, 'weight': 3}).add_to(m1)
                for c in st.session_state['mapa_geral']: folium.GeoJson(c['geojson'], style_function=lambda x, col=c['cor']: {'fillColor': col, 'color': col, 'fillOpacity': 0.6, 'weight': 1}).add_to(m1)
                folium.LayerControl().add_to(m1)
                st_folium(m1, width="100%", height=500, returned_objects=[])

        with tab2:
            st.markdown("### Declividade")
            if st.button("⛰️ Mapear Relevo", use_container_width=True):
                with st.spinner("Calculando..."):
                    st.session_state['fig_declividade'] = plotar_declividade_estatica(dados_geo['gdf_web'])
            if st.session_state.get('fig_declividade'): st.pyplot(st.session_state['fig_declividade'], use_container_width=True)

        with tab3:
            st.markdown("### Hidrografia")
            c1, c2 = st.columns(2)
            with c1:
                st.info("🌊 **Análise de Cursos Hídricos**")
                if st.button("🔍 Verificar Rios (Vetorial)", use_container_width=True):
                    with st.spinner("Analisando base de hidrografia..."):
                        res_h, _ = executar_varredura_paralela(BASES_HIDRO, dados_geo)
                        st.session_state['res_hidro'] = res_h
                        st.session_state['fase_hidro'] = True
                if st.session_state.get('fase_hidro'):
                    if st.session_state['res_hidro']:
                        rios_dict = {}
                        for r in st.session_state['res_hidro']:
                            k = f"{r['Identificação']} ({r['Extra'].get('Regime','N/D')})"
                            rios_dict[k] = rios_dict.get(k, 0) + 1
                        st.warning(f"⚠️ {len(rios_dict)} corpos d'água distintos.")
                        for k, v in rios_dict.items(): st.markdown(f"- **{k}**: {v} segmento(s) mapeado(s).")
                    else: st.success("✅ Nenhum rio cruzando.")
            with c2:
                st.info("🗺️ **Mapa de Hidrografia (Raster)**")
                if st.button("🖼️ Carregar Mapa SEMADESC", use_container_width=True):
                    with st.spinner("Gerando mapa estático dos rios..."):
                        st.session_state['fig_hidro'] = plotar_hidrografia_imasul_estatica(dados_geo['gdf_web'])
                if st.session_state.get('fig_hidro'): st.pyplot(st.session_state['fig_hidro'], use_container_width=True)

        with tab4:
            st.markdown("### Fiscalização, Calor e Alertas")
            if st.button("🔥 Rastrear Infrações e Calor", type="primary", use_container_width=True):
                with st.spinner("Analisando..."):
                    res, mapa = executar_varredura_paralela(BASES_FISCALIZACAO, dados_geo)
                    st.session_state['res_fisc'] = res
                    st.session_state['map_fisc'] = mapa
                    st.session_state['fase_fisc'] = True
            if st.session_state.get('fase_fisc'):
                if st.session_state['res_fisc']:
                    st.error(f"🔥 {len(st.session_state['res_fisc'])} registros encontrados.")
                    df_show = [{k:v for k,v in r.items() if k!='Extra'} for r in st.session_state['res_fisc']]
                    st.dataframe(df_show, use_container_width=True)
                    m4 = folium.Map(location=dados_geo['centro'], zoom_start=12)
                    m4.fit_bounds([[dados_geo['bounds'][1], dados_geo['bounds'][0]], [dados_geo['bounds'][3], dados_geo['bounds'][2]]])
                    folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m4)
                    folium.GeoJson(dados_geo['geojson_folium'], style_function=lambda x: {'fillColor': 'yellow', 'color': 'yellow', 'fillOpacity': 0.1, 'weight': 3}).add_to(m4)
                    for c in st.session_state['map_fisc']:
                        if c['tipo']=='ponto': folium.CircleMarker([c['geojson']['features'][0]['geometry']['coordinates'][1], c['geojson']['features'][0]['geometry']['coordinates'][0]], radius=5, color='orange', fill=True, tooltip="Foco de Calor").add_to(m4)
                        else: folium.GeoJson(c['geojson'], style_function=lambda x: {'fillColor': 'red', 'color': 'red', 'fillOpacity': 0.7, 'weight': 2}).add_to(m4)
                    folium.LayerControl().add_to(m4)
                    st_folium(m4, width="100%", height=500, returned_objects=[])
                else: st.success("✅ Nada consta.")

        with tab5:
            st.markdown("### Licenciamento & Confronto de Dados")
            if st.button("🍒 Cruzar Dados (Licenças vs Alertas)", type="primary", use_container_width=True):
                with st.spinner("Analisando..."):
                    res, mapa = executar_varredura_paralela(BASES_LICENCAS, dados_geo)
                    st.session_state['res_lic'] = res
                    st.session_state['map_lic'] = mapa
                    st.session_state['fase_lic'] = True
            if st.session_state.get('fase_lic'):
                if st.session_state['res_lic']:
                    st.success(f"📄 {len(st.session_state['res_lic'])} licenças encontradas.")
                    df_show = [{k:v for k,v in r.items() if k!='Extra'} for r in st.session_state['res_lic']]
                    st.dataframe(df_show, use_container_width=True)
                else: st.info("ℹ️ Nenhuma licença digital encontrada.")
                
                st.divider()
                st.markdown("#### ⚔️ O Veredito do Mutum (Confronto)")

                m5 = folium.Map(location=dados_geo['centro'], zoom_start=12)
                m5.fit_bounds([[dados_geo['bounds'][1], dados_geo['bounds'][0]], [dados_geo['bounds'][3], dados_geo['bounds'][2]]])
                folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m5)
                folium.GeoJson(dados_geo['geojson_folium'], style_function=lambda x: {'fillColor': 'none', 'color': 'yellow', 'weight': 2}).add_to(m5)
                
                if st.session_state.get('map_lic'):
                    for c in st.session_state['map_lic']: folium.GeoJson(c['geojson'], name=f"Licença: {c['nome']}", style_function=lambda x: {'fillColor': '#00FF00', 'color': '#006400', 'fillOpacity': 0.4, 'weight': 1}, tooltip=c['nome']).add_to(m5)
                
                if st.session_state.get('map_fisc'):
                    for c in st.session_state['map_fisc']:
                         if c['tipo']!='ponto': folium.GeoJson(c['geojson'], name=f"Alerta: {c['nome']}", style_function=lambda x: {'fillColor': '#FF0000', 'color': '#8B0000', 'fillOpacity': 0.6, 'weight': 1}, tooltip=c['nome']).add_to(m5)
                
                folium.LayerControl().add_to(m5)
                st_folium(m5, width="100%", height=600, returned_objects=[])
