
from .models import Census, Csv
from base.tests import BaseTestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import os

class CensusTestCase(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.census = Census(voting_id=1, voter_id=1)
        self.census.save()

    def tearDown(self):
        super().tearDown()
        self.census = None

    def test_check_vote_permissions(self):
        response = self.client.get('/census/{}/?voter_id={}'.format(1, 2), format='json')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), 'Invalid voter')

        response = self.client.get('/census/{}/?voter_id={}'.format(1, 1), format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), 'Valid voter')

    def test_list_voting(self):
        response = self.client.get('/census/?voting_id={}'.format(1), format='json')
        self.assertEqual(response.status_code, 401)

        self.login(user='noadmin')
        response = self.client.get('/census/?voting_id={}'.format(1), format='json')
        self.assertEqual(response.status_code, 403)

        self.login()
        response = self.client.get('/census/?voting_id={}'.format(1), format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'voters': [1]})

    def test_add_new_voters_conflict(self):
        data = {'voting_id': 1, 'voters': [1]}
        response = self.client.post('/census/', data, format='json')
        self.assertEqual(response.status_code, 401)

        self.login(user='noadmin')
        response = self.client.post('/census/', data, format='json')
        self.assertEqual(response.status_code, 403)

        self.login()
        response = self.client.post('/census/', data, format='json')
        #self.assertEqual(response.status_code, 409)

    def test_add_new_voters(self):
        data = {'voting_id': 2, 'voters': [1,2,3,4]}
        response = self.client.post('/census/', data, format='json')
        self.assertEqual(response.status_code, 401)

        self.login(user='noadmin')
        response = self.client.post('/census/', data, format='json')
        self.assertEqual(response.status_code, 403)

        self.login()
        response = self.client.post('/census/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(data.get('voters')), Census.objects.count() - 1)

    def test_destroy_voter(self):
        data = {'voters': [1]}
        response = self.client.delete('/census/{}/'.format(1), data, format='json')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(0, Census.objects.count())

class SeleniumCensusTestCase(StaticLiveServerTestCase):
    
    def setUp(self):
        #Load base test functionality for decide
        self.base = BaseTestCase()
        self.base.setUp()

        options = webdriver.ChromeOptions()
        options.headless = False
        self.driver = webdriver.Chrome(options=options)

        super().setUp()    

    def tearDown(self):
        super().tearDown()
        self.driver.quit()
        self.base.tearDown()
    
    def test_empty_csv(self):                    
        self.driver.get(f'{self.live_server_url}/census/upload')  
        ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) 
        self.driver.find_element_by_id('id_file_name').send_keys(ROOT_DIR + "/csvs/test_empty.csv")
        self.driver.find_element_by_id('confirmar').click()
        time.sleep(1)

        assert self.driver.find_element_by_xpath("//*[contains(text(), 'The submitted file is empty.')]").text == 'The submitted file is empty.'

    def test_full_csv_voting_or_voter_dont_exist(self):   
       #Create voting  
       self.driver.get(f'{self.live_server_url}/admin/')  
       self.driver.find_element_by_name('username').send_keys("admin")
       self.driver.find_element_by_name('password').send_keys("qwerty",Keys.ENTER)   

       self.driver.find_element(By.CSS_SELECTOR, ".model-auth .addlink").click()
       self.driver.find_element(By.ID, "id_name").send_keys("localhost")
       self.driver.find_element(By.ID, "id_url").send_keys("http://localhost:8000")
       self.driver.find_element(By.NAME, "_save").click()
       self.driver.find_element(By.LINK_TEXT, "Home").click()

       self.driver.find_element(By.CSS_SELECTOR, ".model-question .addlink").click()
       self.driver.find_element(By.ID, "id_desc").send_keys("Pregunta votación")

       self.driver.find_element(By.ID, "id_options-0-option").click()
       self.driver.find_element(By.ID, "id_options-0-option").send_keys("A")

       self.driver.find_element(By.ID, "id_options-1-option").click()
       self.driver.find_element(By.ID, "id_options-1-option").send_keys("B")
       self.driver.find_element(By.NAME, "_save").click()
       self.driver.find_element(By.LINK_TEXT, "Home").click()

       self.driver.find_element(By.CSS_SELECTOR, ".model-question .addlink").click()
       self.driver.find_element(By.ID, "id_desc").send_keys("Pregunta 2 votación")

       self.driver.find_element(By.ID, "id_options-0-option").click()
       self.driver.find_element(By.ID, "id_options-0-option").send_keys("C")

       self.driver.find_element(By.ID, "id_options-1-option").click()
       self.driver.find_element(By.ID, "id_options-1-option").send_keys("D")
       self.driver.find_element(By.NAME, "_save").click()
       self.driver.find_element(By.LINK_TEXT, "Home").click()
       
       self.driver.find_element(By.CSS_SELECTOR, ".model-voting .addlink").click()
       self.driver.find_element(By.ID, "id_name").send_keys("Votación 1")
       self.driver.find_element(By.ID, "id_desc").send_keys("Votación prueba")

       dropdown = self.driver.find_element(By.ID, "id_question")
       dropdown.find_element(By.XPATH, "//option[. = 'Pregunta votación']").click()

       dropdown = self.driver.find_element(By.ID, "id_auths")
       dropdown.find_element(By.XPATH, "//option[. = 'http://localhost:8000']").click()

       self.driver.find_element(By.NAME, "_save").click()
       self.driver.find_element(By.LINK_TEXT, "Home").click()   

       self.driver.get(f'{self.live_server_url}/census/upload')  
       ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
       self.driver.find_element_by_id('id_file_name').send_keys(ROOT_DIR + "/csvs/test_full.csv")
       self.driver.find_element_by_id('confirmar').click()

       self.assertEqual(Csv.objects.count(), 1)

    def test_not_csv(self):                    
        self.driver.get(f'{self.live_server_url}/census/upload')  
        ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        self.driver.find_element_by_id('id_file_name').send_keys(ROOT_DIR + "/csvs/test.txt")
        self.driver.find_element_by_id('confirmar').click()

        self.assertEqual(Census.objects.count(), 0)
        self.assertEqual(Csv.objects.count(), 1)
    
    def test_zno_sense_csv(self):                    
        self.driver.get(f'{self.live_server_url}/census/upload')  
        ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        self.driver.find_element_by_id('id_file_name').send_keys(ROOT_DIR + "/csvs/test_no_sense.csv")
        self.driver.find_element_by_id('confirmar').click()
        # time.sleep(30)

        self.assertEqual(Census.objects.count(), 0)
        self.assertEqual(Csv.objects.count(), 1)

    def test_zdelete_csv(self):                    
        self.driver.get(f'{self.live_server_url}/census/upload')
        ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) 
        self.driver.find_element_by_id('id_file_name').send_keys(ROOT_DIR + "/csvs/test.txt")
        self.driver.find_element_by_id('confirmar').click()

        self.assertEqual(Census.objects.count(), 0)
        self.assertEqual(Csv.objects.count(), 1)

        self.driver.get(f'{self.live_server_url}/admin/')  
        self.driver.find_element_by_name('username').send_keys("admin")
        self.driver.find_element_by_name('password').send_keys("qwerty",Keys.ENTER) 

        self.driver.find_element_by_xpath("//*[contains(text(), 'Csvs')]").click()
        self.driver.find_element_by_class_name("action-select").click()
        self.driver.find_element_by_name("action").click()
        self.driver.find_element_by_xpath("//*[contains(text(), 'Delete selected csvs')]").click()
        self.driver.find_element_by_class_name("button").click()
        self.driver.find_element_by_xpath("//input[@type='submit']").click()

        self.assertEqual(Csv.objects.count(), 0)
