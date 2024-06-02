# Web Scraping al sitio Open Food Facts
# Enlace: https://fr.openfoodfacts.org/


# Nos enfocarmeos en los embalajes plásticos
# Enlace: https://fr.openfoodfacts.org/conditionnement/plastique

# Para ver los permisos que tenemos para hacer WebScraping en el sitio, hay que poner /robots.txt

# Dependencias para trabajar con Scrapy
import scrapy
from scrapy import Request
from scrapy.http import HtmlResponse
import time

# Dependencias para trabajar con Selenium
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException



class SpiderOpenFood(scrapy.Spider):
    name = 'open_food'
    start_urls = [
        'https://fr.openfoodfacts.org/categorie/boissons-avec-sucre-ajoute'        
    ]

    custom_settings = {
        'FEEDS':{
            'open_food_boissons_avec_sucre.json':{
                'format': 'json',
                'encoding': 'utf8',
                'store_empty': False,
                'fields': None,
                'indent': 4,
                'item_export_kwargs':{
                    'export_empty_fields': True,
                },
            },
        },
        "ROBOTSTXT_OBEY": True,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',
        'DOWNLOAD_DELAY': 20,  # 10 segundos de espera entre las solicitudes
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,  # Limita a 2 solicitudes simultáneas por dominio
    }


    def parse(self, response):
        # comenzamos a medir el tiempo de ejecución
        start_time = time.time()

        # Obtenemos la cantida de paginas a iterar
        page_numbers = response.xpath('//ul[@id="pages"]/li/a/text()').getall()
        # Ver el valor en console:
        # $x('//ul[@id="pages"]/li/a/text()').map(x=>x.wholeText);
        
        # La lista obtenida es: ["1","2","3","4","661","662","663","Suivant"]
        # Como queremos iterar todas las paginas, necesitamos el número mayor (como entero)
        total_pages = int(page_numbers[-2])
        #total_pages = 2
        # Obtenemos la url del sitio que queremos obtener la información
        principal = response.url

        # Como probaremos mientras tanto, definiremos el range en 1 página (obtenemos solo 100 productos)... luego iteraremos todo para obtener todos los registros del sitio. 
        for page in range(1,total_pages+1):

            # Formamos la url actual: con la url principal y el número de la misma al que queremos ir...
            current_url = f'{principal}/{page}'

            # Cargamos la página con el objeto driver de Selenium
            self.driver.get(current_url)

            # Esperamos a que la página cargue completamente...
            try:
                element = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, '//ul[@id="products_match_all"]'))
                )
            except TimeoutException:
                self.logger.warning("Timeout al esperar el elemento. La página podría haber cambiado")
                return

            # Actualizamos el objeto response con el contenido dinámico
            body = self.driver.page_source
            response = HtmlResponse(self.driver.current_url, body=body, encoding='utf-8', request=response)

            # Obtenemos los enlaces de los productos en la página
            links_products = self.get_links(response)

            # Obtenemos la información de cada enlace en la página
            for link in links_products:
                yield Request(link, callback=self.parse_content_product, cb_kwargs={'url':link})
            

        end_time = time.time()
        execution_time = end_time - start_time
        self.logger.info(f'Tiempo de ejecución: {execution_time} segundos')
        print(execution_time)

    def parse_content_product(self, response, **kwargs):
        url = kwargs['url']
        basic_data = self.get_basic_data(response)
        nutritional_data = self.get_nutritional_data(response)
        environment_data = self.get_environment_data(response)

        yield {
            'url': url,
            'basic_data': basic_data,
            'nutritional_data': nutritional_data,
            'environment_data': environment_data
        }


    # Obtenemos todos los enlaces que se encuentran en la página actual
    def get_links(self, response):
        return response.xpath('//ul[@id="products_match_all"]/li/a/@href').getall()
    

    def get_basic_data(self, response):
        return {
            'title': response.xpath('//h2[@class="title-1"]/text()').get(),
            'bar_code': response.xpath('//span[@id="barcode"]/text()').get(),   # p[@id="barcode_paragraph"]/
            'image': response.xpath('//img[@id="og_image"]/@src').get(),
            'generic_name': response.xpath('//span[@id="field_generic_name_value"]/span/text()').get(),
            'quantity': response.xpath('//span[@id="field_quantity_value"]/text()').get(),
            'packaging': response.xpath('//span[@id="field_packaging_value"]/a/text()').getall(),
            'brands': response.xpath('//span[@id="field_brands_value"]/a/text()').get(),
            'categories': response.xpath('//span[@id="field_categories_value"]/a/text()').getall(),
            'labels': {
                'name': response.xpath('//span[@id="field_labels_value"]/a/text()').getall(),
                'image': response.xpath('//span[@id="field_labels_value"]/img/@src').get()
            },
            'manufacturing': response.xpath('//span[@id="field_manufacturing_places_value"]/a/text()').getall(),
            'countries': response.xpath('//span[@id="field_countries_value"]/a/text()').getall()
        }   
    
    def get_nutritional_data(self, response):
        return {
            'nutriscore': {
                'image': response.xpath('//div[@id="product_summary"]/ul/li/a[@href="#panel_nutriscore"]/div/div/div[@class="img_attr"]/img/@src').get(),
                'grade': response.xpath('//a[@href="#panel_nutriscore"]/div/div/div[@class="attr_text"]/h4/text()').get(),
                'content': response.xpath('//a[@href="#panel_nutriscore"]/div/div/div[@class="attr_text"]/span/text()').get()
            },
            'nova':{
                'image': response.xpath('//div[@id="product_summary"]/ul/li/a[@href="#panel_nova"]/div/div/div[@class="img_attr"]/img/@src').get(),
                'grade': response.xpath('//a[@href="#panel_nova"]/div/div/div[@class="attr_text"]/h4/text()').get(),
                'content': response.xpath('//a[@href="#panel_nova"]/div/div/div[@class="attr_text"]/span/text()').get()
            }
        }


    def get_environment_data(self, response):
        return {
            'ecoscore': {
                'image': response.xpath('//a[@href="#panel_ecoscore_content"]/img/@src').get(),
                'grade': response.xpath('//a[@href="#panel_ecoscore_content"]/h4/text()').get(),
                'content': response.xpath('//a[@href="#panel_ecoscore_content"]/span/text()').get()
            },
            'packaging': {
                'image': response.xpath('//ul[@id="panel_packaging_recycling"]/li/a/img/@src').get(),
                'image_label': response.xpath('//div[@id="image_box_packaging"]/figure/a/img/@src').get(),
                'content': response.xpath('//a[@href="#panel_packaging_recycling_content"]/h4/text()').get(),
                'element_emballage': {
                    'element': response.xpath('//div[@id="panel_packaging_components_content"]/div/div/div/text()').getall(),
                    'material': response.xpath('//div[@id="panel_packaging_components_content"]/div/div/div/strong/text()').getall()
                },
                'materials': {
                    'columns': response.xpath('//div[@id="panel_packaging_materials_content"]/div/table/thead/tr/th/text()').getall(),
                    'rows': response.xpath('//div[@id="panel_packaging_materials_content"]/div/table/tbody/tr/td/span/text()').getall()
                }
            },
            'transport': {
                'image': response.xpath('//a[@href="#panel_origins_of_ingredients_content"]/img/@src').get(),
                'title_image': response.xpath('//a[@href="#panel_origins_of_ingredients_content"]/h4/text()').get(),
                'content': response.xpath('//a[@href="#panel_origins_of_ingredients_content"]/span/text()').get(),
                'origins_table':{
                    'columns': response.xpath('//div[@id="panel_origins_of_ingredients_content"]/div/table/thead/tr/th/text()').getall(),
                    'rows': response.xpath('//div[@id="panel_origins_of_ingredients_content"]/div/table/thead/tr/td/span/text()').getall()
                }
            }
        }





