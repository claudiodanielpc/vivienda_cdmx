import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os
import random
import re
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import vivienda_cdmx.tools.tidytext as tt
import vivienda_cdmx.tools.tipo_cambio as tc
import vivienda_cdmx.tools.amenities as am
from tqdm import tqdm

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'}

options = webdriver.EdgeOptions()
# Add the arguments for Edge
options.add_argument("-inprivate")  # For private browsing in Edge
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-cache")
options.add_argument("--disable-cookies")


def equalize_lists(main_list, *lists):
    main_length = len(main_list)
    for lst in lists:
        while len(lst) < main_length:
            lst.append(None)


# Easybroker

def easybroker():
    # base_url = "https://www.easybroker.com/mx/inmuebles?page={}&search_criteria%5Blocation_ids%5D=86640&search_criteria%5Boperation_type%5D=&update_url=true"
    #base_url = "https://www.easybroker.com/mx/inmuebles?page={}&search_criteria%5Bcurrency_id%5D=10&search_criteria%5Blocation_ids%5D=86618&search_criteria%5Bmax_price%5D=&search_criteria%5Bmin_price%5D=&search_criteria%5Boperation_type%5D=sale&search_criteria%5Bproperty_type_ids%5D%5B%5D=29058&update_url=true"
    base_url="https://www.easyaviso.com/mx/inmuebles/casas-en-venta-en-ciudad-de-mexico?page={}"
    all_data_frames = []

    for page_num in tqdm(range(1, 101), desc="Scraping Easybroker"):
        url = base_url.format(page_num)
        r = requests.get(url, headers=headers)
        sopa = BeautifulSoup(r.text, 'html.parser')

        # The scraping logic for each page.
        recamaras, bathrooms, superficie, direcciones, ofertas, precios, latitud, longitud = [], [], [], [], [], [], [], []

        for precio in sopa.find_all('li', class_='price'):
            precios.append(precio.text.strip())
        for coord in sopa.find_all('li', class_='property__component'):
            latitud.append(coord.get('data-lat'))
            longitud.append(coord.get('data-long'))
        for div in sopa.find_all('div', class_='features'):
            match = re.search(r'(\d+)\s*recámaras', div.text)
            recamaras.append(int(match.group(1)) if match else None)
            match = re.search(r'(\d+)\s*baños', div.text)
            bathrooms.append(int(match.group(1)) if match else None)
            match = re.search(r'(\d+\.?\d*)\s*m²', div.text)
            superficie.append(float(match.group(1)) if match else None)
        for element in sopa.find_all('div', class_='property__content property-content'):
            direcciones.append(element.find('div', class_='location').text.strip())
        for title in sopa.find_all('a', class_='title'):
            ofertas.append(title.text.strip())

        precios = [price for price in precios if "En Renta" not in price]

        equalize_lists(ofertas, recamaras, bathrooms, superficie, direcciones, precios, latitud, longitud)

        data_frame = pd.DataFrame({
            'oferta': ofertas, 'precio': precios, 'mts_const': superficie, 'direccion': direcciones,
            'bathrooms': bathrooms, 'recamaras': recamaras, 'lat': latitud,
            'lon': longitud, 'fuente': 'easybroker'
        })

        # Post-processing steps...
        data_frame["oferta"] = data_frame["oferta"].apply(tt.limpia_texto)
        data_frame["precio"] = data_frame["precio"].fillna("")
        data_frame = data_frame[~data_frame["precio"].str.contains("m²")]
        data_frame["precio"] = (data_frame["precio"].apply(tt.limpia_moneda)
                                .str.replace("$", "", regex=False)
                                .str.replace("Consulte precio", "0", regex=False)
                                .str.replace("En Venta", "", regex=False)
                                .str.replace("\n", "", regex=False))
        # Eliminar aquellos que contengan "En Renta" en precio
        data_frame = data_frame[~data_frame["precio"].str.contains("En Renta")]
        # Eliminar aquellos que contenga "por ha" en precio
        data_frame = data_frame[~data_frame["precio"].str.contains("por ha")]

        # Reemplazar "US" por "" y multiplicar por tipo de cambio
        # Si precio tiene "US", reemplazar por "" y multiplicar por tipo de cambio. Si no, dejar igual

        # Apply the condition using a lambda function
        data_frame["precio"] = data_frame["precio"].apply(
            lambda x: float(x.replace("US", "")) * tc.usd() if "US" in x else x)
        data_frame["precio"] = pd.to_numeric(data_frame["precio"], errors='coerce')
        # Eliminar aquellos que sean NA
        data_frame = data_frame[data_frame["precio"].notna()]
        # Precio a float
        data_frame["precio"] = data_frame["precio"].astype(float)
        # Eliminar "\n" de precio
        data_frame = data_frame[data_frame["precio"] != 0]


        all_data_frames.append(data_frame)
        time.sleep(random.randint(1, 3))

    # Combine all the dataframes from each page into one.
    combined_df = pd.concat(all_data_frames, ignore_index=True)
    # Añadir fecha de consulta
    combined_df["fecha_consulta"] = pd.to_datetime("today")
    return combined_df



def lamudi():
    url_basica = "https://www.lamudi.com.mx/distrito-federal/casa/for-sale/"
    paginacion = "?page="

    all_data = pd.DataFrame()  # To store data from elements
    all_complemento_data = pd.DataFrame()  # To store data from complemento

    for i in tqdm(range(1, 101), desc="Scrapear Lamudi"):
        response = requests.get(url_basica + paginacion + str(i), headers=headers)
        time.sleep(random.randint(1, 3))
        soup = BeautifulSoup(response.text, "html.parser")

        elements = soup.find_all("div", class_="listing listing-card item")
        complemento = soup.find_all("script", type="application/ld+json")

        # Temporary lists for elements data
        oferta, precios, bedrooms, bathrooms, superficie, urls = [], [], [], [], [], []

        for element in elements:
            # Similar data extraction logic as before
            oferta.append(element.find("div", class_="listing-card__title").text.strip() if element.find("div",
                                                                                                         class_="listing-card__title") else None)
            precios.append(
                element.find("div", class_="price").text.strip() if element.find("div", class_="price") else None)
            bedrooms.append(element.find("div", class_="bedrooms").parent.text.strip() if element.find("div",
                                                                                                       class_="bedrooms") else None)
            bathrooms.append(element.find("div", class_="bathrooms").parent.text.strip() if element.find("div",
                                                                                                         class_="bathrooms") else None)
            superficie.append(
                element.find("div", class_="area").parent.text.strip() if element.find("div", class_="area") else None)
            url_fragment = element.get('data-href') or element.find('a')['href'] if element.find('a') else None
            full_url = "https://www.lamudi.com.mx" + url_fragment if url_fragment else None
            urls.append(full_url)

        page_data = pd.DataFrame(
            {"oferta": oferta, "precio": precios, "recamaras": bedrooms, "bathrooms": bathrooms, "size": superficie,
             "url": urls})
        all_data = pd.concat([all_data, page_data], ignore_index=True)

        # Complemento data processing
        if complemento:
            data_json = json.loads(complemento[0].text)[0]['about']
            descripcion, latitud, longitud, oferta_complemento, url_complemento = [], [], [], [], []

            for item in data_json:
                latitud.append(item['geo']['latitude'] if 'latitude' in item['geo'] else None)
                longitud.append(item['geo']['longitude'] if 'longitude' in item['geo'] else None)
                oferta_complemento.append(item['name'] if 'name' in item else None)
                url_complemento.append(item['url'] if 'url' in item else None)
                descripcion.append(item["description"] if "description" in item else None)

            complemento_page_data = pd.DataFrame(
                {"oferta": oferta_complemento, "lat": latitud, "lon": longitud, "url": url_complemento,
                 "descripcion": descripcion})
            all_complemento_data = pd.concat([all_complemento_data, complemento_page_data], ignore_index=True)

    # Merge the data from elements and complemento based on the URL
    final_data = pd.merge(all_data, all_complemento_data, on="url", how="left")
    # Eliminar oferta_y
    final_data = final_data.drop(columns=["oferta_y", "url"])
    # Renombrar oferta_x a oferta
    final_data = final_data.rename(columns={"oferta_x": "oferta"})
    final_data["oferta"] = final_data["oferta"].apply(lambda x: tt.limpia_texto(x))
    final_data["descripcion"] = final_data["descripcion"].apply(lambda x: tt.limpia_texto(x))
    final_data = final_data[~final_data["precio"].str.contains("Desde")]
    final_data['precio'] = final_data['precio'].apply(lambda x: tt.limpia_moneda(x))
    final_data["precio"] = final_data["precio"].str.replace("$", "", regex=False)
    final_data['amount'] = final_data['precio'].str.extract('(\d+[\d,.]*)')
    final_data['moneda'] = final_data['precio'].str.extract('([A-Za-z]+)')
    final_data = final_data.drop(columns=['precio'])
    # Renombrar columna amount a precio
    final_data = final_data.rename(columns={'amount': 'precio'})
    final_data["precio"] = final_data["precio"].astype(float)
    final_data['precio'] = final_data.apply(lambda x: x['precio'] * tc.usd() if x['moneda'] == 'USD' else x['precio'],
                                            axis=1)
    final_data['mts_const'] = final_data['size'].str.split('(\d+)', expand=True)[1]
    final_data['mts_const'] = final_data['mts_const'].astype(float)
    # Eliminar columna moneda
    final_data = final_data.drop(columns=['moneda'])
    final_data = final_data.drop(columns=['size'])


    # Añadir fecha de consulta
    final_data["fecha_consulta"] = pd.to_datetime("today")
    final_data["fuente"] = "lamudi"

    return final_data









