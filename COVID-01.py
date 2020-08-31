# -*- coding: utf-8 -*-
"""
Created on Sun Aug 30 19:22:40 2020

Author: Daniel Gómez

Version: 1.0

"""

import pandas as pd
import datetime as dt

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
             'Country', 
             'New_cases', 
             'New_deaths']]

#Agrupar paises y definir la fecha del día uno
data_country = data[['Country','Country_code','Date_reported']].groupby(['Country','Country_code']).min()
data_country.reset_index(inplace=True)
data_country.rename(columns={'Date_reported':'Date_one'}, inplace=True)

#Crea calendario basico en base a las fechas minima y maxima de la data completa
cal_start = data['Date_reported'].min()
cal_end = data['Date_reported'].max()

l_date=[]
l_n=[]
l_country=[]
l_country_code=[]
l_n_ep=[]
for i in range(0, data_country.shape[0]):
    n=0
    d=cal_start
    while d < cal_end:
        d=cal_start + dt.timedelta(days=n)
        n+=1
        l_country.append(data_country['Country'].tolist()[i])
        l_country_code.append(data_country['Country_code'].tolist()[i])
        l_date.append(d)
        l_n.append(n)
        diff = d - data_country['Date_one'].tolist()[i]
        diff = diff.days+1
        if diff<1:
            diff=0
        l_n_ep.append(diff)
        
calendar=pd.DataFrame({'Country':l_country, 
                       'Country_code':l_country_code, 
                       'Date':l_date, 
                       'Pandemic_day':l_n, 
                       'Epidemic_day':l_n_ep})

data.drop('Country_code', axis=1, inplace=True)
data_final = calendar.merge(data, how='left', left_on=['Country','Date'], right_on=['Country','Date_reported'])
data_final.drop('Date_reported', axis=1, inplace=True)
data_final['New_deaths'].fillna(0,inplace=True)
data_final['New_cases'].fillna(0,inplace=True)

data_final.to_excel('COVID-01.xlsx')