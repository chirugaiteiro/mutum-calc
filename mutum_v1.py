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

# --- IMPORTAÇÕES PARA O PLOT ESTÁTICO ---
import matplotlib.pyplot as plt
from PIL import Image
from io import BytesIO
import matplotlib.patheffects as pe

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="M.U.T.U.M. - MS", page_icon="🐦", layout="wide")

# --- LISTAS DE BASES ---
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
URL_WMS_EXERCITO = "https://bdgex.eb.mil.br/mapcache"

# --- FUNÇÕES AUXILIARES ---
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

# --- PROCESSAMENTO PARALELO (OTIMIZAÇÃO) ---
def processar_uma_base(base, dados_imovel):
    """Função worker que processa uma única base isoladamente."""
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
            legis = "-"
            detalhes_extras = {}
            
            # Extração de Metadados
            if "Licenças" in base['nome']:
                detalhes_extras['Processo'] = buscar_valor_inteligente(attrs, ["num_processo", "processo"])
                detalhes_extras['Atividade'] = buscar_valor_inteligente(attrs, ["atividade", "desc_ativ", "tipologia"])
                detalhes_extras['Situacao'] = buscar_valor_inteligente(attrs, ["situacao", "status"])
                detalhes_extras['Vencimento'] = buscar_valor_inteligente(attrs, ["vencimento", "data_venc", "validade"])
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
            
            # Tratamento Geométrico
            try:
                if base['tipo'] == 'ponto':
                    poly_base = shape(feat['geometry'])
                    area_txt = "Ponto no Imóvel"; pct_txt = "Foco/Ponto"
                elif base['tipo'] == 'linha':
                    area_txt = "Trecho no Imóvel"; pct_txt = "Intersecção Linear"
                else:
                    if base.get('tipo_fonte') == 'WFS': poly_base = shape(feat['geometry'])
                    elif 'geometry' in feat and 'rings' in feat['geometry']:
                        partes = [Polygon(a) for a in feat['geometry']['rings']]
                        poly_base = unary_union(partes)
            except: poly_base = None

            if poly_base:
                try:
                    if not poly_base.is_valid: poly_base = poly_base.buffer(0)
                    interseccao = None
                    
                    if base.get('tipo_fonte') == 'WFS':
                        aux_gdf = gpd.GeoDataFrame({'geometry': [poly_base]}, crs="EPSG:4674").to_crs(dados_imovel['crs_utm'])
                        interseccao = geom_utm_imovel.intersection(aux_gdf.geometry.iloc[0])
                    else:
                        interseccao = geom_utm_imovel.intersection(poly_base)

                    if not interseccao.is_empty:
                        if base['tipo'] == 'poligono':
                            area_calc = interseccao.area / 10000
                            area_txt = f"{area_calc:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            pct_txt = f"{(area_calc/area_imovel)*100:.2f}%"
                        
                        gdf_conf = gpd.GeoDataFrame({'geometry': [interseccao]}, crs=dados_imovel['crs_utm'])
                        nome_camada = f"{base['nome']}: {nome}"
                        geojson_str = gdf_conf.to_crs(epsg=4326).to_json()
                        cor_atual = gerar_cor_aleatoria()
                        
                        camadas_parcial.append({
                            "nome": nome_camada, "geojson": json.loads(geojson_str), 
                            "tipo": base['tipo'], "cor": cor_atual
                        })
                        
                        resultados_parcial.append({
                            "Base": base['nome'], "Identificação": nome, "Detalhes": legis,
                            "Área (ha)": area_txt, "Status": pct_txt,
                            "Extra": detalhes_extras
                        })
                except: pass
                
    return resultados_parcial, camadas_parcial

def executar_varredura_paralela(lista_bases, dados_imovel):
    """Gerenciador de Threads para execução simultânea."""
    todos_resultados = []
    todas_camadas = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        # Mapeia cada base para uma thread
        future_to_base = {executor.submit(processar_uma_base, base, dados_imovel): base for base in lista_bases}
        
        for future in concurrent.futures.as_completed(future_to_base):
            try:
                res, cam = future.result()
                todos_resultados.extend(res)
                todas_camadas.extend(cam)
            except Exception as exc:
                # Opcional: print(f"Erro na base: {exc}")
                pass
                
    return todos_resultados, todas_camadas

# --- PLOTAGEM ESTÁTICA (COM CORREÇÃO DE HEADER) ---
def plotar_declividade_estatica(gdf_web):
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

def plotar_cartas_exercito_estatica(gdf_web):
    bounds = gdf_web.total_bounds
    margem = 0.015 
    minx, miny, maxx, maxy = bounds[0]-margem, bounds[1]-margem, bounds[2]+margem, bounds[3]+margem
    
    # Header adicionado para simular navegador e evitar bloqueio
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    params = {"SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetMap", "LAYERS": "ctm100", "STYLES": "", "SRS": "EPSG:4326", "BBOX": f"{minx},{miny},{maxx},{maxy}", "WIDTH": "1200", "HEIGHT": "1200", "FORMAT": "image/png"}
    try:
        # Timeout aumentado para 45s pois o Exército é lento
        resp = requests.get(URL_WMS_EXERCITO, params=params, headers=headers, timeout=45)
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content))
            fig, ax = plt.subplots(figsize=(12, 12))
            ax.imshow(img, extent=[minx, maxx, miny, maxy], aspect='auto')
            gdf_web.plot(ax=ax, facecolor='none', edgecolor='blue', linewidth=3, path_effects=[pe.Stroke(linewidth=5, foreground='white'), pe.Normal()])
            ax.set_aspect('equal'); ax.set_axis_off(); ax.set_title("Carta Topográfica (BDGex/Exército)", fontsize=16, color='white', pad=20)
            fig.patch.set_facecolor('#0E1117')
            return fig
    except: return None
    return None

@st.cache_data(show_spinner=False)
def carregar_geometria_imovel(file_bytes):
    temp_dir = tempfile.mkdtemp()
    path_zip = os.path.join(temp_dir, "temp.zip")
    with open(path_zip, "wb") as f: f.write(file_bytes)
    with zipfile.ZipFile(path_zip, 'r') as zip_ref: zip_ref.extractall(temp_dir)
    arquivos_shp = [f for f in os.listdir(temp_dir) if f.lower().endswith('.shp')]
    if not arquivos_shp: return None, "Nenhum .shp encontrado."
    try:
        gdf = gpd.read_file(os.path.join(temp_dir, arquivos_shp[0]))
        if not gdf.crs: gdf.set_crs(epsg=31981, inplace=True)
        else: gdf = gdf.to_crs(epsg=31981)
        gdf['geometry'] = gdf.geometry.buffer(0)
        geom_utm = gdf.geometry.iloc[0]
        area_ha = geom_utm.area / 10000
        gdf_geo = gdf.to_crs(epsg=4674)
        geom_geo = gdf_geo.geometry.iloc[0]
        json_poly = json.dumps({"rings": [list(geom_geo.exterior.coords)], "spatialReference": {"wkid": 4674}})
        ponto = geom_geo.centroid
        json_point = json.dumps({"x": ponto.x, "y": ponto.y, "spatialReference": {"wkid": 4674}})
        gdf_folium = gdf.to_crs(epsg=4326)
        geojson_folium = gdf_folium.to_json()
        bounds = gdf_folium.total_bounds.tolist() 
        centro = [ponto.y, ponto.x]
        bounds_4674 = gdf_geo.total_bounds.tolist()
        return {"geom_utm": geom_utm, "json_poly": json_poly, "json_point": json_point, "area_ha": area_ha, "geojson_folium": geojson_folium, "gdf_web": gdf_folium, "bounds": bounds, "bounds_4674": bounds_4674, "centro": centro, "crs_utm": gdf.crs}, None
    except Exception as e: return None, str(e)

# --- INTERFACE PRINCIPAL ---
st.title("🐦 M.U.T.U.M. - Vigilante Ambiental")
st.markdown("##### Ferramenta de Monitoramento Unificado de Terras e Uso em MS")

with st.expander("⚠️ AVISO LEGAL - VERSÃO BETA (Leia antes de usar)", expanded=True):
    st.warning("""
    **ATENÇÃO: ESTA É UMA VERSÃO DE TESTE (BETA 3.5)**
    1. **Fonte de Dados:** Este aplicativo consome dados públicos via APIs (WMS/WFS/REST). Instabilidades externas podem ocorrer.
    2. **Caráter Auxiliar:** As informações aqui apresentadas servem para *triagem rápida* e **NÃO SUBSTITUEM** a consulta oficial aos sistemas do IMASUL.
    3. **Responsabilidade:** O uso das informações é de responsabilidade do analista.
    *Voe com segurança!* 🐦
    """)

uploaded_file = st.file_uploader("📂 Arraste seu Shapefile (.ZIP) para o ninho", type="zip")

if 'arquivo_atual' not in st.session_state or st.session_state['arquivo_atual'] != uploaded_file:
    st.session_state['arquivo_atual'] = uploaded_file
    st.session_state['resultados_geral'] = []
    st.session_state['mapa_geral'] = []
    st.session_state['fase_geral_feita'] = False
    
    st.session_state['resultados_hidro'] = []
    st.session_state['fase_hidro_feita'] = False
    
    st.session_state['resultados_fisc'] = []
    st.session_state['mapa_fisc'] = []
    st.session_state['fase_fisc_feita'] = False

    st.session_state['resultados_lic'] = []
    st.session_state['mapa_lic'] = []
    st.session_state['fase_lic_feita'] = False
    
    st.session_state['fig_declividade'] = None
    st.session_state['fig_cartas'] = None

if uploaded_file:
    with st.spinner("🐦 O Mutum está analisando a geometria do seu arquivo..."):
        dados_geo, erro = carregar_geometria_imovel(uploaded_file.getvalue())
    
    if erro: 
        st.error(f"🍂 Ocorreu um erro ao pousar no arquivo: {erro}")
    else:
        st.info(f"📍 **Pouso confirmado!** Imóvel identificado com **{dados_geo['area_ha']:,.4f} ha**.")
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🔍 1. Restrições", 
            "⛰️ 2. Declividade", 
            "💧 3. Cartas/Hidro", 
            "🔥 4. Fiscalização/Calor", 
            "🍒 5. Licenciamento"
        ])

        with tab1:
            st.markdown("### Monitoramento de Restrições Gerais")
            if st.button("🦅 Levantar Voo (Iniciar Varredura Rápida)", type="primary", use_container_width=True):
                with st.spinner("🐦 Sobrevoando todas as bases simultaneamente..."):
                    # AGORA USANDO A FUNÇÃO PARALELA
                    res, mapa = executar_varredura_paralela(BASES_GERAIS, dados_geo)
                    st.session_state['resultados_geral'] = res
                    st.session_state['mapa_geral'] = mapa
                    st.session_state['fase_geral_feita'] = True
            
            if st.session_state['fase_geral_feita']:
                if st.session_state['resultados_geral']:
                    st.error(f"⚠️ O Mutum avistou **{len(st.session_state['resultados_geral'])}** sobreposições na área.")
                    df_show = [{k:v for k,v in r.items() if k!='Extra' and k!='Status'} for r in st.session_state['resultados_geral']]
                    st.dataframe(df_show, use_container_width=True)
                else: 
                    st.success("✅ Horizonte limpo! O Mutum não detectou restrições gerais nesta área.")
                
                m1 = folium.Map(location=dados_geo['centro'])
                m1.fit_bounds([[dados_geo['bounds'][1], dados_geo['bounds'][0]], [dados_geo['bounds'][3], dados_geo['bounds'][2]]])
                folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m1)
                folium.GeoJson(dados_geo['geojson_folium'], name="📍 Meu Imóvel", style_function=lambda x: {'fillColor': '#ffff00', 'color': '#ffff00', 'fillOpacity': 0.1, 'weight': 3}).add_to(m1)
                for c in st.session_state['mapa_geral']:
                    cor = c.get('cor', '#ff0000')
                    folium.GeoJson(c['geojson'], name=c['nome'], style_function=lambda x, color=cor: {'fillColor': color, 'color': color, 'fillOpacity': 0.6, 'weight': 1}, tooltip=c['nome']).add_to(m1)
                folium.LayerControl().add_to(m1)
                st_folium(m1, width="100%", height=500, returned_objects=[])

        with tab2:
            st.markdown("### Mapeamento de Declividade")
            st.caption("Imagem gerada diretamente dos servidores do IMASUL.")
            st.markdown("""<div style='background-color:#262730;padding:10px;border-radius:5px;color:#FAFAFA;display:flex;gap:15px;flex-wrap:wrap;justify-content:center;border:1px solid #41424C;'><div><span style='color:#00a884;'>■</span> 0-5°</div><div><span style='color:#4c0073;'>■</span> 5-16°</div><div><span style='color:#ffeb00;'>■</span> 16-25°</div><div><span style='color:#ff3700;'>■</span> 25-45° (AUR)</div><div><span style='color:#000000;border:1px solid #fff;'>■</span> >45° (APP)</div></div>""", unsafe_allow_html=True)
            if st.button("⛰️ Mapear Relevo", use_container_width=True):
                with st.spinner("🐦 O Mutum está calculando o esforço de voo..."):
                    st.session_state['fig_declividade'] = plotar_declividade_estatica(dados_geo['gdf_web'])
            if st.session_state['fig_declividade']:
                st.pyplot(st.session_state['fig_declividade'], use_container_width=True)

        with tab3:
            st.markdown("### Cartografia & Hidrografia")
            if st.button("🗺️ Consultar Cartas do Exército", use_container_width=True):
                with st.spinner("🐦 Buscando referências cartográficas no BDGex (Isso pode demorar um pouco)..."):
                    st.session_state['fig_cartas'] = plotar_cartas_exercito_estatica(dados_geo['gdf_web'])
            if st.session_state['fig_cartas']:
                st.pyplot(st.session_state['fig_cartas'], use_container_width=True)

        with tab4:
            st.markdown("### 🚨 Fiscalização, Calor e Alertas")
            if st.button("🔥 Rastrear Infrações e Calor", type="primary", use_container_width=True):
                with st.spinner("🐦 O Mutum ativou a visão térmica (INPE) e o radar de infrações..."):
                    # AGORA USANDO A FUNÇÃO PARALELA
                    res, mapa = executar_varredura_paralela(BASES_FISCALIZACAO, dados_geo)
                    st.session_state['resultados_fisc'] = res
                    st.session_state['mapa_fisc'] = mapa
                    st.session_state['fase_fisc_feita'] = True
            
            if st.session_state['fase_fisc_feita']:
                if st.session_state['resultados_fisc']:
                    agrupados = {}
                    for item in st.session_state['resultados_fisc']:
                        chave = f"{item['Base']} | ID: {item['Identificação']}"
                        try:
                            if "Ponto" in item['Área (ha)'] or "Trecho" in item['Área (ha)']: area_float = 0
                            else: area_float = parse_float_br(item['Área (ha)'])
                        except: area_float = 0
                        if chave not in agrupados: agrupados[chave] = {'dados': item, 'area_total': area_float, 'fragmentos': 1}
                        else:
                            agrupados[chave]['area_total'] += area_float
                            agrupados[chave]['fragmentos'] += 1
                    
                    st.error(f"🔥 Alerta no Ninho! Foram encontrados **{len(agrupados)}** registros de infração, calor ou alerta.")
                    for chave, obj in agrupados.items():
                        item = obj['dados']
                        area_str = "Ponto/Trecho" if "Ponto" in item['Área (ha)'] else f"{obj['area_total']:,.4f} ha".replace(",", "X").replace(".", ",").replace("X", ".")
                        titulo = f"🚫 {chave} - {area_str}"
                        with st.expander(titulo):
                            d = item.get('Extra', {})
                            if "MapBiomas" in item['Base']:
                                st.markdown(f"**Data Detecção:** {d.get('Data Detecção', '-')}")
                                st.markdown(f"**Bioma:** {d.get('Bioma', '-')}")
                            elif "Focos de Calor" in item['Base']:
                                st.markdown(f"**Satélite:** {d.get('Satélite', '-')}")
                                st.markdown(f"**Data/Hora:** {d.get('Data Hora', '-')}")
                            else:
                                c1, c2 = st.columns(2)
                                with c1:
                                    st.markdown(f"**Autuado:** {d.get('Autuado', '-')}")
                                    st.markdown(f"**CPF/CNPJ:** {d.get('CPF_CNPJ', '-')}")
                                with c2:
                                    st.markdown(f"**Data:** {d.get('Data', '-')}")
                                    st.markdown(f"**Infração:** {d.get('Infração', '-')}")
                    
                    m4 = folium.Map(location=dados_geo['centro'])
                    m4.fit_bounds([[dados_geo['bounds'][1], dados_geo['bounds'][0]], [dados_geo['bounds'][3], dados_geo['bounds'][2]]])
                    folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m4)
                    folium.GeoJson(dados_geo['geojson_folium'], name="📍 Meu Imóvel", style_function=lambda x: {'fillColor': '#ffff00', 'color': '#ffff00', 'fillOpacity': 0.1, 'weight': 3}).add_to(m4)
                    for c in st.session_state['mapa_fisc']:
                        cor = c.get('cor', '#8B0000')
                        if c['tipo'] == 'ponto':
                            folium.CircleMarker(location=[c['geojson']['features'][0]['geometry']['coordinates'][1], c['geojson']['features'][0]['geometry']['coordinates'][0]], radius=5, color='orange', fill=True, tooltip="Foco de Calor").add_to(m4)
                        else:
                            folium.GeoJson(c['geojson'], name=c['nome'], style_function=lambda x, color=cor: {'fillColor': color, 'color': color, 'fillOpacity': 0.7, 'weight': 2}, tooltip=c['nome']).add_to(m4)
                    folium.LayerControl().add_to(m4)
                    st_folium(m4, width="100%", height=500, returned_objects=[])
                else: st.success("✅ Tudo calmo! O Mutum não encontrou passivos ambientais ou fogo recente.")

        with tab5:
            st.markdown("### 🍒 Licenciamento & Confronto de Dados")
            st.caption("A Cereja do Bolo: Cruzamento entre o que foi autorizado (Licenças) e o que foi alertado (Fiscalização).")
            
            if st.button("🍒 Cruzar Dados (Licenças vs Alertas)", type="primary", use_container_width=True):
                with st.spinner("🐦 O Mutum está comparando a papelada com a realidade..."):
                    # AGORA USANDO A FUNÇÃO PARALELA TAMBÉM
                    res_lic, mapa_lic = executar_varredura_paralela(BASES_LICENCAS, dados_geo)
                    st.session_state['resultados_lic'] = res_lic
                    st.session_state['mapa_lic'] = mapa_lic
                    st.session_state['fase_lic_feita'] = True
            
            if st.session_state['fase_lic_feita']:
                if st.session_state['resultados_lic']:
                    st.success(f"📄 O Mutum encontrou **{len(st.session_state['resultados_lic'])}** licenças emitidas para esta área.")
                    lista_display = []
                    for lic in st.session_state['resultados_lic']:
                        d = lic.get('Extra', {})
                        lista_display.append({
                            "Documento": lic['Identificação'],
                            "Atividade": d.get('Atividade', '-'),
                            "Processo": d.get('Processo', '-'),
                            "Área (ha)": lic['Área (ha)']
                        })
                    st.dataframe(lista_display, use_container_width=True)
                else:
                    st.info("ℹ️ Nenhuma licença digital encontrada no sistema para esta área.")

                st.divider()
                st.markdown("#### ⚔️ O Veredito do Mutum (Confronto)")
                
                if not st.session_state.get('fase_fisc_feita'):
                    st.warning("⚠️ O Mutum precisa visitar a aba **'4. Fiscalização'** antes de dar o veredito.")
                else:
                    if not st.session_state['resultados_fisc']:
                        st.success("✅ Sem alertas de fiscalização para confrontar. Aparentemente tudo regular!")
                    else:
                        alertas_sem_licenca = 0
                        for alerta_geo in st.session_state['mapa_fisc']:
                            if alerta_geo['tipo'] == 'ponto': continue
                            try:
                                geom_raw_alerta = alerta_geo['geojson']['features'][0]['geometry']
                                shape_alerta = shape(geom_raw_alerta)
                                area_alerta = shape_alerta.area
                                area_interseccao_total = 0
                                licencas_cobertura = []
                                for lic_geo in st.session_state['mapa_lic']:
                                    geom_raw_lic = lic_geo['geojson']['features'][0]['geometry']
                                    shape_lic = shape(geom_raw_lic)
                                    intersec = shape_alerta.intersection(shape_lic)
                                    if not intersec.is_empty:
                                        area_interseccao_total += intersec.area
                                        licencas_cobertura.append(lic_geo['nome'])
                                pct_coberto = (area_interseccao_total / area_alerta) * 100 if area_alerta > 0 else 0
                                nome_alerta = alerta_geo['nome']
                                if pct_coberto > 90:
                                    st.success(f"✅ **Supressão Autorizada:** O alerta '{nome_alerta}' está {pct_coberto:.1f}% coberto pelas licenças.")
                                elif pct_coberto > 5:
                                    st.warning(f"⚠️ **Atenção Parcial:** O alerta '{nome_alerta}' tem apenas {pct_coberto:.1f}% de cobertura.")
                                else:
                                    st.error(f"🚨 **Passivo Identificado:** O alerta '{nome_alerta}' NÃO possui cobertura de licença.")
                                    alertas_sem_licenca += 1
                            except: pass
                        
                        if alertas_sem_licenca > 0:
                            st.markdown(f"**Resumo:** O Mutum detectou **{alertas_sem_licenca}** polígonos suspeitos sem licença digital correspondente.")
                    
                    m5 = folium.Map(location=dados_geo['centro'])
                    m5.fit_bounds([[dados_geo['bounds'][1], dados_geo['bounds'][0]], [dados_geo['bounds'][3], dados_geo['bounds'][2]]])
                    folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m5)
                    folium.GeoJson(dados_geo['geojson_folium'], style_function=lambda x: {'fillColor': 'none', 'color': 'yellow', 'weight': 2}).add_to(m5)
                    
                    if st.session_state['mapa_lic']:
                        for c in st.session_state['mapa_lic']:
                            folium.GeoJson(c['geojson'], name=f"Licença: {c['nome']}", style_function=lambda x: {'fillColor': '#00FF00', 'color': '#006400', 'fillOpacity': 0.4, 'weight': 1}, tooltip=c['nome']).add_to(m5)
                    
                    if st.session_state['mapa_fisc']:
                        for c in st.session_state['mapa_fisc']:
                            if c['tipo'] != 'ponto':
                                folium.GeoJson(c['geojson'], name=f"Alerta: {c['nome']}", style_function=lambda x: {'fillColor': '#FF0000', 'color': '#8B0000', 'fillOpacity': 0.6, 'weight': 1}, tooltip=c['nome']).add_to(m5)
                        
                    folium.LayerControl().add_to(m5)
                    st_folium(m5, width="100%", height=600, returned_objects=[])
