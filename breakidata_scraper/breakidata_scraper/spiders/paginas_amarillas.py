import json
import re

import scrapy
import pymysql
import pandas as pd
import numpy as np

NUMERO_DE_ENTRADAS_POR_PAGINA = 30


class QuotesSpider(scrapy.Spider):
    name = "quotes"

    def __init__(self):
        self.consultar_actividades()
        self.total = 0

    def start_requests(self):
        for url in self.urls_actividades:
            yield scrapy.Request(url=url, callback=self.parse_actividad, meta={'proxy': 'http://83.149.70.159:13012'})

    def consultar_actividades(self):
        conexion_mysql = pymysql.connect(host='45.82.82.5', user='brekiadata_yo', passwd='.^w-}YuoIYrK',
                                         db='brekiada_central')
        consulta_bd_producto = "SELECT referencia,suburl_pag_original FROM brekiada_central.bd_producto WHERE activo=1 and referencia LIKE 'BRK%' and bd_producto.id_fuente = 1 or bd_producto.id_fuente = 2"

        tabla_bd_producto = pd.read_sql(consulta_bd_producto, conexion_mysql)
        self.urls_actividades = "https://www.paginasamarillas.es/a/" + tabla_bd_producto['suburl_pag_original'].values
        self.referencias = tabla_bd_producto['referencia'].values
        conexion_mysql.close()

    def parse_actividad(self, response):
        actividad = response.url.replace('https://www.paginasamarillas.es/a/', '')[:-1]  # Se le ha añadido / al final
        referencia = self.referencias[np.where(self.urls_actividades == response.url[:-1])]

        numero_entradas = normaliza_entero_entre_parentesis_y_puntuado(response.css('.h1').xpath('text()')
                                                                       .get())
        numero_paginas = numero_entradas // NUMERO_DE_ENTRADAS_POR_PAGINA
        yield response
        for indice in range(1, numero_paginas + 1):
            yield scrapy.Request(url=response.url + str(indice), callback=self.parse_pagina_de_actividad,
                                 meta={'proxy': 'http://83.149.70.159:13012'})

    def parse_pagina_de_actividad(self, response):
        imagenes = response.css('.imagen')

        for imagen in imagenes:
            url_entrada = imagen.xpath('@href').get()
            if url_entrada.startswith('https://www.paginasamarillas.es/f/'):
                yield scrapy.Request(url=url_entrada, callback=self.parse, meta={'proxy': 'http://83.149.70.159:13012'})

    def parse(self, response):
        url = response.url
        nombre_empresa = response.selector.xpath('//h1/text()').get()
        telefonos = response.xpath('//span[@itemprop="telephone"]/b/text()').getall()
        direccion = response.xpath('//span[@itemprop="streetAddress"]/b/text()').get()
        cp = response.xpath('//span[@itemprop="postalCode"]/b/text()').get()
        localidades = list(filter(lambda localidad: localidad not in [' (', ') ',')',', '], response.xpath(
            '//span[@itemprop="address"]/span[@class="text-symbol"]/text()').getall() + response.xpath(
            '//span[@itemprop="addressLocality"]/text()').getall()))
        provincia = response.xpath('//span[@data-yext="addressState"]/text()').get()
        telefonos = response.xpath('//span[@itemprop="telephone"]/b/text()').getall()
        data_business = response.css('div.contenedor[itemtype^="http://schema.org/"]')[0].xpath('@data-business').get()
        data_json = json.loads(data_business)

        try:
            email = data_json['customerMail']
        except:
            email = None

        try:
            web = data_json['mapInfo']['adWebEstablecimiento']
        except:
            web = None

        try:
            latitud = data_json['location']['latitude']
            longitud = data_json['location']['longitude']
        except:
            latitud = None
            longitud = None

        try:
            actividad = data_json['info']['activity']
        except:
            actividad = None

        subsector = response.xpath('//div[@class="actividades p-3 "]/p/text()').get().upper()
        # print(localidades, provincia, telefonos, email, web, latitud, longitud)

        try:
            migas_de_pan = response.xpath('//li[@class="breadcrumb-item"]/a/span/text()').getall()

        except:
            migas_de_pan = None

        try:
            tipos_alojamiento = ['ESTRELLAS', 'ESTRELLA', 'ESPIGA', 'CATEGORÍA', 'LLAVE']
            alojamiento = list(
                filter(lambda miga: (
                        any(tipo in miga.upper() for tipo in tipos_alojamiento) and any(i.isdigit() for i in miga)),
                       migas_de_pan))[-1].upper()
            tipo_alojamiento = \
                [tipo_alojamiento for tipo_alojamiento in tipos_alojamiento if tipo_alojamiento in alojamiento.split()][
                    -1]
            if tipo_alojamiento == 'ESTRELLAS':
                tipo_alojamiento = 'ESTRELLA'
            estrellas = [estrella for estrella in alojamiento if estrella.isdigit()][-1]
        except Exception as e:
            alojamiento = None
            tipo_alojamiento = None
            estrellas = None

        descripcion = response.xpath('//div[@itemprop="description"]/text()').getall()
        habitaciones_regex = re.search(r'<li>Número de habitaciones: (?P<habitaciones>.*?)<\/li>', response.text,
                                       re.IGNORECASE)
        try:
            habitaciones = habitaciones_regex.group('habitaciones')
        except:
            habitaciones = None

        fecha_constitucion_regex = re.search(r'<li>Fecha de constitución: (?P<fecha>.*?)<\/li>', response.text,
                                             re.IGNORECASE)
        try:
            fecha_constitucion = fecha_constitucion_regex.group('fecha')
        except:
            fecha_constitucion = None

        forma_social_regex = re.search(r'<li>Forma social: (?P<forma_social>.*?)<\/li>', response.text, re.IGNORECASE)
        try:
            forma_social = forma_social_regex.group('forma_social')
        except:
            forma_social = None

        actividad_CNAE_regex = re.search(r'<li>Actividad CNAE: (?P<actividad_cnae>.*?)<\/li>', response.text,
                                         re.IGNORECASE)
        try:
            actividad_CNAE = actividad_CNAE_regex.group('actividad_cnae')
        except:
            actividad_CNAE = None

        rango_num_empleados_regex = re.search(r'<li>Rango Nº empleados: (?P<rango_num_empleados>.*?)<\/li>',
                                              response.text, re.IGNORECASE)
        try:
            rango_num_empleados = rango_num_empleados_regex.group('rango_num_empleados')
        except:
            rango_num_empleados = None

        rango_facturacion_regex = re.search(r'<li>Rango de facturación: (?P<rango_facturacion>.*?)<\/li>',
                                            response.text, re.IGNORECASE)
        try:
            rango_facturacion = rango_facturacion_regex.group('rango_facturacion')
        except:
            rango_facturacion = None

        rango_capital_social_regex = re.search(r'Su capital social es de (?P<rango_capital_social>.*?)(?:\. | \.<\/p>)',
                                               response.text, re.IGNORECASE)
        try:
            rango_capital_social = rango_capital_social_regex.group('rango_capital_social')
        except:
            rango_capital_social = None

        print(url, forma_social, actividad_CNAE, rango_num_empleados, rango_facturacion, rango_capital_social)

        print(
            "nombre_empresa:", nombre_empresa, "\n",
            "telefonos:", telefonos, "\n",
            "direccion:", direccion, "\n",
            "cp:", cp, "\n",
            "localidades:", localidades, "\n",
            "provincia:", provincia, "\n",
            "telefonos:", telefonos, "\n",
            "email:", email, "\n",
            "web:", web, "\n",
            "latitud:", latitud, "\n",
            "longitud:", longitud, "\n",
            "actividad:", actividad, "\n",
            "tipo_alojamiento:", tipo_alojamiento, "\n",
            "estrellas:", estrellas, "\n",
            "habitaciones:", habitaciones, "\n",
            "fecha_constitucion:", fecha_constitucion, "\n",
            "forma_social:", forma_social, "\n",
            "actividad_CNAE:", actividad_CNAE, "\n",
            "rango_num_empleados:", rango_num_empleados, "\n",
            "rango_facturacion:", rango_facturacion, "\n",
            "rango_capital_social:", rango_capital_social, "\n",
        )


def normaliza_entero_entre_parentesis_y_puntuado(number):
    return int(number.replace('(', '').replace(')', '').replace('.', ''))
