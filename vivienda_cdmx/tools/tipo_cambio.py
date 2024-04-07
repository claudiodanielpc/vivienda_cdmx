#Obtención de tipos de cambio

import requests


#Dólares a pesos mexicanos
def usd():
    #Obtener tipo de cambio
    banxico="https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF43718/datos/?token=0e825df61e5eca2dd60340f1d39766f5cbefc052fb00f49b257095da3e004921"
    r=requests.get(banxico).json()
    #Obtener último dato
    mxn=r["bmx"]["series"][0]["datos"][-1]["dato"]
    #transformar a float
    mxn=float(mxn)
    return mxn
