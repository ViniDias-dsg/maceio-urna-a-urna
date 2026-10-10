"""Agrega votos por local de votação em Maceió e gera data.json para o mapa.
uso: python3 process.py <csv_secao> <cargo> <saida.json>
"""
import sys, json, re
import pandas as pd
import geopandas as gpd

SEC_CSV, CARGO, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
MCZ = 27855  # código TSE de Maceió
LOC_CSV = '/home/claude/data/maceio_secoes_2026.csv'

cols = ['NR_TURNO', 'SG_UF', 'CD_MUNICIPIO', 'NR_ZONA', 'NR_SECAO', 'DS_CARGO',
        'NR_VOTAVEL', 'NM_VOTAVEL', 'QT_VOTOS', 'NR_LOCAL_VOTACAO']
parts = []
for ch in pd.read_csv(SEC_CSV, sep=';', encoding='latin1', usecols=cols,
                      chunksize=1_000_000, dtype={'CD_MUNICIPIO': int}):
    ch = ch[(ch.CD_MUNICIPIO == MCZ) & (ch.NR_TURNO == 1) & (ch.SG_UF == 'AL')
            & (ch.DS_CARGO.str.upper() == CARGO.upper())]
    if len(ch):
        parts.append(ch)
v = pd.concat(parts)
print('linhas', len(v), 'seções', v.groupby(['NR_ZONA', 'NR_SECAO']).ngroups)

# votos por candidato no município (para a legenda)
tot = v.groupby(['NR_VOTAVEL', 'NM_VOTAVEL']).QT_VOTOS.sum().sort_values(ascending=False)
print(tot.head(15))

# locais (coordenadas oficiais do TSE, 1º turno)
loc = pd.read_csv(LOC_CSV, dtype=str)
loc = loc[loc.NR_TURNO == '1']
loc['lat'] = loc.NR_LATITUDE.str.replace(',', '.').astype(float)
loc['lon'] = loc.NR_LONGITUDE.str.replace(',', '.').astype(float)
loc['aptos'] = loc.QT_ELEITOR_SECAO.astype(int)
L = loc.groupby(['NR_ZONA', 'NR_LOCAL_VOTACAO']).agg(
    nome=('NM_LOCAL_VOTACAO', 'first'), end=('DS_ENDERECO', 'first'),
    bairro_tse=('NM_BAIRRO', 'first'), lat=('lat', 'first'), lon=('lon', 'first'),
    secoes=('NR_SECAO', 'nunique'), aptos=('aptos', 'sum')).reset_index()
L['NR_ZONA'] = L.NR_ZONA.astype(int)
L['NR_LOCAL_VOTACAO'] = L.NR_LOCAL_VOTACAO.astype(int)

# bairro oficial (IBGE 2022) por junção espacial
B = gpd.read_file('/home/claude/build/bairros.gpkg')
g = gpd.GeoDataFrame(L, geometry=gpd.points_from_xy(L.lon, L.lat), crs=B.crs)
g = gpd.sjoin(g, B, how='left', predicate='within')
miss = g.name_neighborhood.isna()
if miss.any():  # pontos na borda/praia: bairro mais próximo
    near = gpd.sjoin_nearest(g[miss].drop(columns=['index_right', 'name_neighborhood']).to_crs(31985),
                             B.to_crs(31985), how='left')
    g.loc[miss, 'name_neighborhood'] = near.name_neighborhood.values
L['bairro'] = g.name_neighborhood.values

def key(n):
    n = int(n)
    return {13: 'lula', 22: 'flavio', 95: 'branco', 96: 'nulo'}.get(n, 'outros')

v['k'] = v.NR_VOTAVEL.map(key)
# liga cada seção ao local onde ela de fato funcionou no 1º turno (cadastro do TSE)
sec = loc[['NR_ZONA', 'NR_SECAO', 'NR_LOCAL_VOTACAO']].drop_duplicates(['NR_ZONA', 'NR_SECAO']).astype(int)
v = v.drop(columns='NR_LOCAL_VOTACAO').merge(sec, on=['NR_ZONA', 'NR_SECAO'], how='left')
print('seções sem local:', v[v.NR_LOCAL_VOTACAO.isna()].groupby(['NR_ZONA','NR_SECAO']).ngroups)
P = v.pivot_table(index=['NR_ZONA', 'NR_LOCAL_VOTACAO'], columns='k', values='QT_VOTOS',
                  aggfunc='sum', fill_value=0).reset_index()
P['NR_LOCAL_VOTACAO'] = P.NR_LOCAL_VOTACAO.astype(int)
for c in ['lula', 'flavio', 'outros', 'branco', 'nulo']:
    if c not in P:
        P[c] = 0
D = L.merge(P, on=['NR_ZONA', 'NR_LOCAL_VOTACAO'], how='inner')
print('locais com votos', len(D), 'de', len(L), '| sem coord:', len(P) - len(D))

def title(s):
    s = re.sub(r'\s+', ' ', str(s)).strip()
    small = {'DE', 'DA', 'DO', 'DAS', 'DOS', 'E'}
    return ' '.join(w.capitalize() if w not in small else w.lower() for w in s.split(' '))

locais = []
for r in D.itertuples():
    locais.append({
        'z': r.NR_ZONA, 'n': r.NR_LOCAL_VOTACAO, 'nome': title(r.nome),
        'end': title(r.end), 'b': r.bairro, 'lat': round(r.lat, 6), 'lon': round(r.lon, 6),
        's': int(r.secoes), 'ap': int(r.aptos), 'L': int(r.lula), 'F': int(r.flavio),
        'O': int(r.outros), 'Br': int(r.branco), 'Nu': int(r.nulo)})

cands = [{'num': int(k[0]), 'nome': k[1], 'votos': int(x)} for k, x in tot.items()]
json.dump({'cargo': CARGO, 'locais': locais, 'candidatos': cands},
          open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
print('ok', OUT)
