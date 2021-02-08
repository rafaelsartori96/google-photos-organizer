import os
import json
import shutil
import argparse

from glob import glob
from datetime import datetime, timezone


#  Pegamos na entrada a pasta que iremos executar
parser = argparse.ArgumentParser(description='Procuramos fotos do Google Photos Takeout.')
parser.add_argument('--relatorio', nargs='?', default='imagens.json', help='relatório JSON de imagens encontradas')
parser.add_argument('--copiar', nargs='?', help='pasta raiz para copiar imagens')
parser.add_argument('pasta', nargs='?', default='.', help='pasta raiz para busca')
args = parser.parse_args()


print('Arquivo relatório:', args.relatorio)
print('Caminho entrado para busca:', args.pasta)
if args.copiar is not None:
    print('Pasta para copiar imagens catalogadas:', args.copiar)
print()
print('Buscando pastas...')

# Caminho de imagens não encontradas (apagadas)
imagens_nao_encontradas = []
imagens_sem_geo = {}
imagens_com_geo = {}
imagens_falhas = []

# Procuramos todas as pastas recursivamente
pastas = glob(f'{args.pasta}/**/')[::-1]
print('Iniciando busca por imagens...')
try:
    for indice, caminho in enumerate(pastas):
        print(f'{indice + 1} de {len(pastas)} pastas percorridas', end='\r')
        # Para cada JSON na pasta, abrimos e verificamos a existência de uma imagem
        for caminho_json in glob(f'{caminho}/*.json'):
            with open(caminho_json, 'r') as arquivo:
                dicionario = json.load(arquivo)

                # Ignoramos JSON que não fala de imagem
                if 'title' not in dicionario:
                    continue
                if 'photoTakenTime' not in dicionario:
                    print('photoTakenTime não disponível')
                    continue
                if 'timestamp' not in dicionario['photoTakenTime']:
                    print('timestamp não disponível')
                    continue
                timestamp = int(dicionario['photoTakenTime']['timestamp'])
                caminho_imagem = f"{caminho}{dicionario['title']}"

                dict_imagem = {
                    'caminho_imagem': caminho_imagem,
                    'pasta': caminho,
                    'caminho_json': caminho_json,
                    'timestamp': timestamp,
                }

                # Pegamos a data a partir do timestamp
                data = datetime.fromtimestamp(timestamp)
                data = data.replace(tzinfo=timezone.utc).astimezone(tz=None)

                # Ignoramos imagens que não existam
                if not os.path.isfile(caminho_imagem):
                    imagens_nao_encontradas.append(dict_imagem)
                    continue

                def mover_imagem(caminho_inicial, pasta_final, caminho_final):
                    os.makedirs(pasta_final, exist_ok=True)
                    #shutil.copy(caminho_inicial, caminho_final)
                    try:
                        shutil.move(caminho_inicial, caminho_final)
                        return True
                    except Exception as e:
                        print('\nFalha ao mover arquivo', caminho_inicial, e)
                        return False

                # Definimos o que faremos com imagens sem geolocalização
                def trabalhar_imagem_sem_geo():
                    mes_ano = f'{data.year}-{data.month}'

                    # Adicionamos essa informação ao dicionário
                    dict_imagem['mes_ano'] = mes_ano

                    # Adicionamos o caminho final da imagem
                    if args.copiar is not None:
                        extensao = dicionario['title'][::-1].split('.', 1)[0][::-1]
                        nome_final = '.'.join([data.strftime('%Y%m%d-%H%M%S%z'), extensao])
                        caminho_final = f"{args.copiar}{mes_ano}/{nome_final}"
                        dict_imagem['caminho_final'] = caminho_final

                    # Adicionamos o dicionário à lista dependendo da data
                    if mes_ano not in imagens_sem_geo:
                        imagens_sem_geo[mes_ano] = []
                    imagens_sem_geo[mes_ano].append(dict_imagem)

                    # Finalmente, tentamos mover a imagem
                    if args.copiar is not None:
                        if not mover_imagem(caminho_imagem, f"{args.copiar}{mes_ano}", caminho_final):
                            imagens_falhas.append(dict_imagem)


                # Agora temos JSON e uma imagem, precisamos verificar as que possuem ou não coordenadas
                if 'geoData' not in dicionario:
                    trabalhar_imagem_sem_geo()
                    continue
                geoData = dicionario['geoData']
                if 'latitude' not in geoData:
                    trabalhar_imagem_sem_geo()
                    continue
                if 'longitude' not in geoData:
                    trabalhar_imagem_sem_geo()
                    continue
                if geoData['latitude'] == 0.0 and geoData['longitude'] == 0.0:
                    trabalhar_imagem_sem_geo()
                    continue
                latitude = geoData['latitude']
                longitude = geoData['longitude']

                # Aqui, trabalharemos com imagem com geolocalização

                # Agora temos uma imagem com coordenada
                dict_imagem['latitude'] = latitude
                dict_imagem['longitude'] = longitude

                # Colocamos a imagem por regiões
                # Arredondamos os valores para regiões
                latitude = round(latitude, 1)
                longitude = round(longitude, 1)
                par = f'{latitude},{longitude}'

                # Adicionamos o caminho final da imagem
                if args.copiar is not None:
                    extensao = dicionario['title'][::-1].split('.', 1)[0][::-1]
                    nome_final = '.'.join([data.strftime('%Y%m%d-%H%M%S%z'), extensao])
                    caminho_final = f"{args.copiar}{par}/{nome_final}"
                    dict_imagem['caminho_final'] = caminho_final

                # Asseguramos de que temos a região no dicionário
                if par not in imagens_com_geo:
                    imagens_com_geo[par] = []
                # Colocamos na lista
                imagens_com_geo[par].append(dict_imagem)

                # Finalmente, tentamos mover a imagem
                if args.copiar is not None:
                    if not mover_imagem(caminho_imagem, f"{args.copiar}{par}", caminho_final):
                        imagens_falhas.append(dict_imagem)

except Exception as e:
    print()
    print('Falha ao analisar imagens:', e)
    pass

# Fazemos um relatório
print(f'{indice} de {len(pastas)} pastas percorridas')
print('Fazendo relatório...')
relatorio = {
    'imagens_nao_encontradas': imagens_nao_encontradas,
    'imagens_com_geo': imagens_com_geo,
    'imagens_sem_geo': imagens_sem_geo,
    'imagens_falhas': imagens_falhas,
}

# Ao final, imprimimos o relatório em arquivo JSON
with open(args.relatorio, 'w') as arquivo_relatorio:
    json.dump(relatorio, arquivo_relatorio, indent=4)
