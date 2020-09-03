# -*- coding: utf-8 -*-
"""
Created on Sun Aug 30 19:22:40 2020

Author: Daniel Gómez

Version: 2.0

"""

import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt
from datapackage import Package
import numpy as np

# Extracción del paquete y posterior CSV con información de países.
package = Package('https://datahub.io/core/country-codes/datapackage.json')
for resource in package.resources:
    if resource.descriptor['datahub']['type'] == 'derived/csv':
        ctry_data = pd.read_csv(resource.descriptor['path'])

# Definición de campos que efectivamente utilizaremos
ctry_data = ctry_data[['official_name_en', 
                       'official_name_es', 
                       'ISO3166-1-Alpha-2',
                       'ISO3166-1-Alpha-3',
                       'CLDR display name',
                       'Continent',
                       'Region Name', 
                       'Sub-region Name']]

# Corrección especifica de información faltante para Taiwan y Antartica, y agregar Otros, Kosovo (opcional)
ctry_data[(ctry_data['ISO3166-1-Alpha-2']=='TW')] = ctry_data[(ctry_data['ISO3166-1-Alpha-2']=='TW')].fillna({'official_name_en':'Taiwan', 'official_name_es':'Taiwan', 'Region Name':'Asia', 'Sub-region Name':'Eastern Asia'})
ctry_data[(ctry_data['ISO3166-1-Alpha-2']=='AQ')] = ctry_data[(ctry_data['ISO3166-1-Alpha-2']=='AQ')].fillna('Antarctica')
ctry_data = ctry_data.append({'official_name_en':'Other',
                              'official_name_es':'Otro',
                              'ISO3166-1-Alpha-2':'OO',
                              'ISO3166-1-Alpha-3':'OOO',
                              'CLDR display name':'Other',
                              'Continent':'OO',
                              'Region Name':'Other',
                              'Sub-region Name':'Other'},
                             ignore_index=True)
ctry_data = ctry_data.append({'official_name_en':'Kosovo',
                              'official_name_es':'Kosovo',
                              'ISO3166-1-Alpha-2':'XK',
                              'ISO3166-1-Alpha-3':'XKS',
                              'CLDR display name':'Kosovo',
                              'Continent':'EU',
                              'Region Name':'Europe',
                              'Sub-region Name':'Southern Europe'},
                             ignore_index=True)

#Extracción de CSV de sitio de la onu
data = pd.read_csv('https://covid19.who.int/WHO-COVID-19-global-data.csv', 
                   parse_dates=['Date_reported'])

#Trim de etiquetas de columna ... issue del CSV de origen.
dic={}
for col in data.columns.values.tolist():
    dic[col]=col.strip()
data.rename(columns=dic, inplace=True)
data = data[['Date_reported', 
             'Country_code', 
             'New_cases', 
             'New_deaths']]

#Ajuste de Others
data['Country_code'].replace([' '],'OO',inplace=True)

# Alinea los periodos entre fechas a un día (opcional)
data_g=data.groupby('Country_code').apply(lambda x: x.set_index('Date_reported').resample('1D').first())

# Calcula los valores de percentil 25, 75 y la mediana (50)
data_q25 = data_g.groupby(level=0)[['New_cases','New_deaths']].apply(lambda x: x.rolling(window=14, min_periods=1).quantile(0.25)).reset_index()
data_q75 = data_g.groupby(level=0)[['New_cases','New_deaths']].apply(lambda x: x.rolling(window=14, min_periods=1).quantile(0.75)).reset_index()
data_q50 = data_g.groupby(level=0)[['New_cases','New_deaths']].apply(lambda x: x.rolling(window=14, min_periods=1).quantile(0.5)).reset_index()

# Ajuste de Others
data_q25['Country_code'].replace([' '],'OO',inplace=True)
data_q75['Country_code'].replace([' '],'OO',inplace=True)
data_q50['Country_code'].replace([' '],'OO',inplace=True)

# Definición de Outliers
data_ol = data_q25.merge(data_q75,how='left',on=['Date_reported','Country_code'],suffixes=('_q25','_q75'))
data_ol['New_cases_min']=data_ol['New_cases_q25']-((data_ol['New_cases_q75']-data_ol['New_cases_q25'])*1.5)
data_ol['New_cases_max']=data_ol['New_cases_q75']+((data_ol['New_cases_q75']-data_ol['New_cases_q25'])*1.5)
data_ol['New_deaths_min']=data_ol['New_deaths_q25']-((data_ol['New_deaths_q75']-data_ol['New_deaths_q25'])*1.5)
data_ol['New_deaths_max']=data_ol['New_deaths_q75']+((data_ol['New_deaths_q75']-data_ol['New_deaths_q25'])*1.5)
data_ol.drop(['New_cases_q25','New_deaths_q25','New_cases_q75','New_deaths_q75'],axis=1,inplace=True)
data_ol = data_ol.merge(data_q50,how='left',on=['Date_reported','Country_code'])
data_ol.rename(columns={'New_cases':'New_cases_q50','New_deaths':'New_deaths_q50'},inplace=True)

# Eliminación de Outliers
data_b = data.merge(data_ol,how='left',on=['Country_code','Date_reported'])
data_b['New_cases_s']=np.select([(data_b['New_cases']<data_b['New_cases_min']),
                                 (data_b['New_cases']>=data_b['New_cases_min'])&(data_b['New_cases']<=data_b['New_cases_max']),
                                 (data_b['New_cases']>data_b['New_cases_max'])],
                                [data_b['New_cases_q50'],
                                 data_b['New_cases'],
                                 data_b['New_cases_q50']])
data_b['New_deaths_s']=np.select([(data_b['New_deaths']<data_b['New_deaths_min']),
                                 (data_b['New_deaths']>=data_b['New_deaths_min'])&(data_b['New_deaths']<=data_b['New_deaths_max']),
                                 (data_b['New_deaths']>data_b['New_deaths_max'])],
                                [data_b['New_deaths_q50'],
                                 data_b['New_deaths'],
                                 data_b['New_deaths_q50']])
data_b.drop(['New_cases',
             'New_deaths',
             'New_cases_min',
             'New_cases_max',
             'New_deaths_min',
             'New_deaths_max',
             'New_cases_q50',
             'New_deaths_q50'],
            axis=1,
            inplace=True)

# Calcula valores medios en el periodo definido
data_g=data_b.groupby('Country_code').apply(lambda x: x.set_index('Date_reported').resample('1D').first())
data_f = data_g.groupby(level=0)[['New_cases_s','New_deaths_s']].apply(lambda x: x.rolling(window=14, min_periods=1).mean()).reset_index()
data_f= data_b.merge(data_f,how='left',on=['Date_reported','Country_code'],suffixes=('1','2'))

# Corrige el country code de Others
data_f['Country_code'].replace([' '],'OO',inplace=True)

# Unir tabla de datos diarios con tabla suavizada.
data = data.merge(data_f,how='left',on=['Country_code','Date_reported'],suffixes=('','_s'))

# Eliminar NaN en caso de que existan (opcional)
data.dropna(inplace=True)

# Definir día epidémico y pandémico
data_ep = data[['Country_code','Date_reported']].groupby('Country_code').min().reset_index()
data = data.merge(data_ep,how='left',on='Country_code',suffixes=('','_a'))
data['Date_reported_b']=data['Date_reported'].min()
data['Epidemic_day']=(data['Date_reported']-data['Date_reported_a']).dt.days + 1
data['Pandemic_day']=(data['Date_reported']-data['Date_reported_b']).dt.days + 1
data.drop(['Date_reported_a','Date_reported_b'],axis=1,inplace=True)

# Agregar información de País
data = data.merge(ctry_data, how='left',left_on='Country_code',right_on='ISO3166-1-Alpha-2')

#Genera archivo excel con los datos
data.to_excel('COVID-01.xlsx')
print('Datos Archivados')

#Diccionario de paises y colores de las curvas (https://python-graph-gallery.com/196-select-one-color-with-matplotlib/)
ctry = {'CL':['red','pink'], 
        'FR':['darkblue','lightblue'],
        'AR':['goldenrod','khaki'],
        'BR':['darkgreen','lightgreen'],
        'US':['black','silver']}

#Curva de contagios
ax=plt.gca()
for x in ctry:
    ctry_name = ctry_data.loc[ctry_data['ISO3166-1-Alpha-2']==x,'official_name_es'].values[0]
    data[(data['Country_code']==x)].plot(figsize=(15,10),kind='line', label=ctry_name, x='Epidemic_day',y='New_cases_s2',ax=ax, color=ctry[x][0])
    data[(data['Country_code']==x)].plot(figsize=(15,10),kind='scatter', x='Epidemic_day',y='New_cases_s1',ax=ax, color=ctry[x][1],title='Curva de Contagios Diarios')
ax.set_xlabel("Dia Epidemico")
ax.set_ylabel("Número de Casos")
plt.savefig('Curva-Contagios.png')
print('Curva de Contagios Archivada')
plt.show()
#Curva de muertos
at=plt.gca()
for x in ctry:
    ctry_name = ctry_data.loc[ctry_data['ISO3166-1-Alpha-2']==x,'official_name_es'].values[0]
    data[(data['Country_code']==x)].plot(figsize=(15,10), kind='line', label=ctry_name, x='Epidemic_day',y='New_deaths_s2',ax=at, color=ctry[x][0])
    data[(data['Country_code']==x)].plot(figsize=(15,10), kind='scatter', x='Epidemic_day',y='New_deaths_s1',ax=at, color=ctry[x][1],title='Curva de Muertos Diarios')
at.set_xlabel("Dia Epidemico")
at.set_ylabel("Número de Muertos")
plt.savefig('Curva-Muertos.png')
print('Curva de Muertos Archivada')
plt.show()