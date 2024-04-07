#Funciones de limpieza para utilizar en medsearch

import re
from unidecode import unidecode 


###Limpieza general de texto
def limpia_texto(text):
    if text is None:
        return ""
    # Elimina caracteres no alfanuméricos, caracteres, puntuación, espacios extras y signos de pesos
    cleaned_text = re.sub(r'[^\w\s.]', '', text).strip()
    # Minúsculas
    cleaned_text = cleaned_text.lower()
    #Eliminar acentos
    cleaned_text = unidecode(cleaned_text)
    #Si el texto dice "merida" y después "yucatan", elimina "yucatan" usando expresiones regulares
    cleaned_text = re.sub(r'(merida)\s(yucatan)', r'\1', cleaned_text)
            
    return cleaned_text

def limpia_moneda(text):
    if text is None:
        return ""
    #Eliminar "\n"
    cleaned_coin = re.sub(r'\n', '', text).strip()
    #Elimina comas
    cleaned_coin = re.sub(r',', '', text).strip()
    #Eliminar signo de pesos
    cleaned_coin = re.sub(r'$', '', cleaned_coin)

    return cleaned_coin