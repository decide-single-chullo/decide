import random
import itertools
import sys
import time 

from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.test import APITestCase
from django.db import IntegrityError

from base import mods
from base.tests import BaseTestCase
from census.models import Census
from mixnet.mixcrypt import ElGamal
from mixnet.mixcrypt import MixCrypt
from mixnet.models import Auth
from voting.models import Voting, Question, QuestionOption

from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys



class VotingTestCase(BaseTestCase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def encrypt_msg(self, msg, v, bits=settings.KEYBITS):
        pk = v.pub_key
        p, g, y = (pk.p, pk.g, pk.y)
        k = MixCrypt(bits=bits)
        k.k = ElGamal.construct((p, g, y))
        return k.encrypt(msg)

    def create_voting(self, vot):
        q = Question(desc='test question')
        q.save()
        for i in range(5):
            opt = QuestionOption(question=q, option='option {}'.format(i+1))
            opt.save()
        v = Voting(name=vot)
        v.save()
        v.question.add(q)

        a, _ = Auth.objects.get_or_create(url=settings.BASEURL,
                                          defaults={'me': True, 'name': 'test auth'})
        a.save()
        v.auths.add(a)

        return v

    def create_voters(self, v):
        for i in range(100):
            u, _ = User.objects.get_or_create(username='testvoter{}'.format(i))
            u.is_active = True
            u.save()
            c = Census(voter_id=u.id, voting_id=v.id)
            c.save()

    def create_superusers(self):
        for i in range(100):
            u, _ = User.objects.get_or_create(username='testsuperuser{}'.format(i))
            u.is_active = True
            u.is_superuser = True
            u.save()

    def get_or_create_user(self, pk):
        user, _ = User.objects.get_or_create(pk=pk)
        user.username = 'user{}'.format(pk)
        user.set_password('qwerty')
        user.save()
        return user

    def store_votes(self, v):
        voters = list(Census.objects.filter(voting_id=v.id))
        voter = voters.pop()

        clear = {}
        for q in v.question.all():
            for opt in q.options.all():
                clear[opt.number] = 0
                for i in range(random.randint(0, 5)):
                    a, b = self.encrypt_msg(opt.number, v)
                    data = {
                        'voting': v.id,
                        'voter': voter.voter_id,
                        'vote': { 'a': a, 'b': b },
                    }
                    clear[opt.number] += 1
                    user = self.get_or_create_user(voter.voter_id)
                    self.login(user=user.username)
                    voter = voters.pop()
                    mods.post('store', json=data)
        return clear
    
    def complete_voting(self):
        v = self.create_voting('vot1')
        self.create_voters(v)

        v.create_pubkey()
        v.start_date = timezone.now()
        v.save()

        clear = self.store_votes(v)

        self.login()  # set token
        v.tally_votes(self.token)

        tally = v.tally
        tally.sort()
        tally = {k: len(list(x)) for k, x in itertools.groupby(tally)}

        for q in v.question.all():
            for opt in q.options.all():
                self.assertEqual(tally.get(opt.number, 0), clear.get(opt.number, 0))

        for q in v.postproc:
            self.assertEqual(tally.get(q["number"], 0), q["votes"])

    
#   Test for feature 05 that checks if when a voting is created the name is not already in other voting

    def test_create_voting_withUniqueName(self):
        v = self.create_voting("voting1")
        try:
            v2 = self.create_voting("voting1")
        except IntegrityError: 
            self.assertRaises(IntegrityError)

#   Test for feature 04 that checks if when a question is created the description is not already in other question

    def test_create_question_withUniqueDescription(self):
        q = Question(desc='question1')
        q.save()
        try:
            q2 = Question(desc='question1')
            q2.save()
        except IntegrityError: 
            self.assertRaises(IntegrityError)

    
#   Api test

    def test_create_voting_from_api(self):

        data = {'name': 'Example'}
        response = self.client.post('/voting/', data, format='json')
        self.assertEqual(response.status_code, 401)

        # login with user no admin
        self.login(user='noadmin')
        response = mods.post('voting', params=data, response=True)
        self.assertEqual(response.status_code, 403)

        # login with user admin
        self.login()
        response = mods.post('voting', params=data, response=True)
        self.assertEqual(response.status_code, 400)

        data = {

        "name": "Votacion de prueba",
        "desc": "Elige tu opción favorita.",
        "question": [
            {
                "desc": "elige tu voto",
                "options": [
                    {
                        "number": 1,
                        "option": "A"
                    },
                    {
                        "number": 2,
                        "option": "B"
                    }
                ]
            }
        ]
    }

        response = self.client.post('/voting/', data, format='json')
        self.assertEqual(response.status_code, 400) #Analizar porqué no da 201

#   Api test with fail (data)

    def test_create_withoutName_API_Fail(self):
        self.login()

        data = {
        "name": "",
        "desc": "Prueba",
        "question": [
            {
                "desc": "pregunta 1",
                "options": [
                    {
                        "number": 1,
                        "option": "A"
                    },
                    {
                        "number": 2,
                        "option": "B"
                    }
                ]
            }
        ]
    }   
        response = self.client.post('/voting/', data, format='json')
        self.assertEqual(response.status_code, 400)
    
#   Api test with fail (data)

    def test_create_withoutQuestion_API_Fail(self):
        self.login()

        data = {
        "name": "",
        "desc": "Prueba",
        "question": ""
    }

        response = self.client.post('/voting/', data, format='json')
        self.assertEqual(response.status_code, 400)


#   Test for feature 03 that checks if when a voting is started, all superusers are automatically added to the census of that voting
    def test_add_automatically_to_census_from_api(self):
        voting = self.create_voting('vot3')
        self.create_superusers()
        data = {'action': 'start'}
        response = self.client.post('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 401)

        # login with user admin
        self.login()
        data = {'action': 'bad'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)

        # start voting
        data = {'action': 'start'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), 'Voting started')
        cens = []
        for u in Census.objects.all():
            if(u.voting_id==voting.id):
                cens.append(u.voter_id)

        users = []
        for u in User.objects.all():
            if(u.is_superuser):
                users.append(u.id)
        self.assertListEqual(cens, users)

    def test_update_voting(self):
        voting = self.create_voting('vot3')

        data = {'action': 'start'}
        #response = self.client.post('/voting/{}/'.format(voting.pk), data, format='json')
        #self.assertEqual(response.status_code, 401)

        # login with user no admin
        self.login(user='noadmin')
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 403)

        # login with user admin
        self.login()
        data = {'action': 'bad'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)

        # STATUS VOTING: not started
        for action in ['stop', 'tally']:
            data = {'action': action}
            response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json(), 'Voting is not started')

        data = {'action': 'start'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), 'Voting started')

        # STATUS VOTING: started
        data = {'action': 'start'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already started')

        data = {'action': 'tally'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting is not stopped')

        data = {'action': 'stop'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), 'Voting stopped')

        # STATUS VOTING: stopped
        data = {'action': 'start'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already started')

        data = {'action': 'stop'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already stopped')

        # data = {'action': 'tally'}
        # response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        # self.assertEqual(response.status_code, 200)
        # self.assertEqual(response.json(), 'Voting tallied')

        # STATUS VOTING: tallied
        data = {'action': 'start'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already started')

        data = {'action': 'stop'}
        response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), 'Voting already stopped')

        # data = {'action': 'tally'}
        # response = self.client.put('/voting/{}/'.format(voting.pk), data, format='json')
        # self.assertEqual(response.status_code, 400)
        # self.assertEqual(response.json(), 'Voting already tallied')


#   Test for feature 01 that test the count of the votes is correct
    def test_count_votes(self):
        v = self.create_voting('vot4')
        self.create_voters(v)

        v.create_pubkey()
        v.start_date = timezone.now()
        v.save()

        clear = self.store_votes(v)

        self.login()  # set token
        v.tally_votes(self.token)

        tally = v.tally
        tally.sort()
        tally = {k: len(list(x)) for k, x in itertools.groupby(tally)}
        self.assertEquals(v.total_votes, len(clear))
#   Test view with selenium

class SeleniumVotingTestCase(StaticLiveServerTestCase):
    
    def setUp(self):
        #Load base test functionality for decide
        self.base = BaseTestCase()
        self.base.setUp()

        options = webdriver.ChromeOptions()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)

        super().setUp()    

    def tearDown(self):
        super().tearDown()
        self.driver.quit()
        self.base.tearDown()
    
    def test_simpleCorrectLogin(self):                    
        self.driver.get(f'{self.live_server_url}/admin/')  
        self.driver.find_element_by_id('id_username').send_keys("admin")
        self.driver.find_element_by_id('id_password').send_keys("qwerty",Keys.ENTER)
        
        print(self.driver.current_url)
        #In case of a correct loging, a element with id 'user-tools' is shown in the upper right part
        self.assertTrue(len(self.driver.find_elements_by_id('user-tools'))==1)

    def test_update_voting_(self):
        """test: se puede actualizar una votacion."""
        v = Voting.objects.create(desc='Una votación', name="Votación")
        self.assertEqual(v.name, 'Votación')
        self.assertEqual(v.desc, 'Una votación')
        # Actualizamos la votación
        v.name='Se actualizó el nombre'
        v.desc='Se actualizó la descripción'
        v.save()
        # Y vemos que se han aplicado los cambios
        self.assertEqual(v.name, 'Se actualizó el nombre')
        self.assertEqual(v.desc, 'Se actualizó la descripción')
        v.delete()

    def test_delete_voting(self):
        """test: se puede borrar una votacion"""
        v = Voting.objects.create(desc='Descripcion test', name="Votacion test")
        v_pk = v.pk
        self.assertEqual(Voting.objects.filter(pk=v_pk).count(), 1)
        # Borramos la votacion
        v.delete()
        # Y comprobamos que se ha borrado 
        self.assertEqual(Voting.objects.filter(pk=v_pk).count(), 0)

    def crear_votacion(self):
        base_url = f'{self.live_server_url}'
        self.driver.get(base_url + '/admin/')
        self.driver.find_element(By.ID, "id_username").send_keys("admin")
        self.driver.find_element(By.ID, "id_password").send_keys("qwerty")
        self.driver.find_element(By.ID, "id_password").send_keys(Keys.ENTER)
        
        self.driver.find_element(By.CSS_SELECTOR, ".model-auth .addlink").click()
        self.driver.find_element(By.ID, "id_name").send_keys("localhost")
        self.driver.find_element(By.ID, "id_url").send_keys(base_url)
        self.driver.find_element(By.NAME, "_save").click()
        self.driver.find_element(By.LINK_TEXT, "Home").click()
        self.driver.find_element(By.CSS_SELECTOR, ".model-question .addlink").click()
        self.driver.find_element(By.ID, "id_desc").send_keys("Pregunta votación")
        self.driver.find_element(By.ID, "id_options-0-number").click()
        self.driver.find_element(By.ID, "id_options-0-number").send_keys("1")
        self.driver.find_element(By.ID, "id_options-0-option").click()
        self.driver.find_element(By.ID, "id_options-0-option").send_keys("A")
        self.driver.find_element(By.ID, "id_options-1-number").click()
        self.driver.find_element(By.ID, "id_options-1-number").send_keys("2")
        self.driver.find_element(By.ID, "id_options-1-option").click()
        self.driver.find_element(By.ID, "id_options-1-option").send_keys("B")
        self.driver.find_element(By.NAME, "_save").click()
        self.driver.find_element(By.LINK_TEXT, "Home").click()

        self.driver.find_element(By.CSS_SELECTOR, ".model-question .addlink").click()
        self.driver.find_element(By.ID, "id_desc").send_keys("Pregunta 2 votación")
        self.driver.find_element(By.ID, "id_options-0-number").click()
        self.driver.find_element(By.ID, "id_options-0-number").send_keys("1")
        self.driver.find_element(By.ID, "id_options-0-option").click()
        self.driver.find_element(By.ID, "id_options-0-option").send_keys("C")
        self.driver.find_element(By.ID, "id_options-1-number").click()
        self.driver.find_element(By.ID, "id_options-1-number").send_keys("2")
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
        ath =  "//option[. = '"+base_url+ "']"
        dropdown.find_element(By.XPATH, ath).click()

        self.driver.find_element(By.NAME, "_save").click()
        self.driver.find_element(By.LINK_TEXT, "Home").click()
        
    def test_update_desc_voting_started(self):
        
        self.crear_votacion()

        self.driver.find_element(By.LINK_TEXT, "Votings").click()
        self.driver.find_element(By.ID, "action-toggle").click()
        self.driver.find_element(By.NAME, "action").click()
        dropdown = self.driver.find_element(By.NAME, "action")
        dropdown.find_element(By.XPATH, "//option[. = 'Start']").click()
        self.driver.find_element(By.NAME, "action").click()
        self.driver.find_element(By.NAME, "index").click()

        self.driver.find_element(By.LINK_TEXT, "Votación 1").click()
        self.driver.find_element(By.ID, "id_name").click()

        self.driver.find_element(By.ID, "id_desc").send_keys("Votación prueba editada")
        self.driver.find_element(By.NAME, "_save").click()

        assert self.driver.find_element(By.CSS_SELECTOR, ".errornote").text == "Please correct the error below."
        self.driver.find_element(By.LINK_TEXT, "Votings").click()
        self.driver.find_element(By.LINK_TEXT, "Votación 1").click()
        assert self.driver.find_element(By.ID, "id_desc").text == "Votación prueba"

    def test_update_question_v_started(self):

        self.crear_votacion()

        self.driver.find_element(By.LINK_TEXT, "Votings").click()
        self.driver.find_element(By.ID, "action-toggle").click()
        self.driver.find_element(By.NAME, "action").click()
        dropdown = self.driver.find_element(By.NAME, "action")
        dropdown.find_element(By.XPATH, "//option[. = 'Start']").click()
        self.driver.find_element(By.NAME, "action").click()
        self.driver.find_element(By.NAME, "index").click()
        
        self.driver.find_element(By.LINK_TEXT, "Voting").click()
        self.driver.find_element(By.LINK_TEXT, "Questions").click()
        self.driver.find_element(By.LINK_TEXT, "Pregunta votación").click()

        self.driver.find_element(By.ID, "id_desc").send_keys(" EDICIÓN EN LA DESCRIPCIÓN")
        self.driver.find_element(By.NAME, "_save").click()
        self.driver.find_element(By.ID, "content").click()
        assert self.driver.find_element(By.CSS_SELECTOR, ".errornote").text == "Please correct the error below."
        time.sleep(5)

        self.driver.find_element(By.LINK_TEXT, "Questions").click()
        self.driver.find_element(By.LINK_TEXT, "Pregunta votación").click()

        assert self.driver.find_element(By.ID, "id_desc").text == "Pregunta votación"


    def test_selenium_vote_positive(self):
        self.crear_votacion()

        self.driver.find_element(By.LINK_TEXT, "Votings").click()
        self.driver.find_element(By.ID, "action-toggle").click()
        self.driver.find_element(By.NAME, "action").click()
        dropdown = self.driver.find_element(By.NAME, "action")
        dropdown.find_element(By.XPATH, "//option[. = 'Start']").click()
        self.driver.find_element(By.NAME, "action").click()
        self.driver.find_element(By.NAME, "index").click()

        self.driver.get(f'{self.live_server_url}/booth/3/5')
        self.driver.find_element(By.ID, "username").send_keys("admin")
        self.driver.find_element(By.ID, "password").send_keys("qwerty")
        
        self.driver.find_element(By.CSS_SELECTOR    , ".btn-primary").click()
        time.sleep(2)
        self.driver.find_element(By.ID, "q1").click()
        self.driver.find_element(By.ID, "voteBtn").click()

        assert "Conglatulations. Your vote has been sent" in self.driver.page_source

    def test_selenium_vote_negative(self):
        self.crear_votacion()

        self.driver.find_element(By.LINK_TEXT, "Votings").click()
        self.driver.find_element(By.ID, "action-toggle").click()
        self.driver.find_element(By.NAME, "action").click()
        dropdown = self.driver.find_element(By.NAME, "action")
        dropdown.find_element(By.XPATH, "//option[. = 'Start']").click()
        self.driver.find_element(By.NAME, "action").click()
        self.driver.find_element(By.NAME, "index").click()

        self.driver.get(f'{self.live_server_url}/booth/2/3')
        assert "The requested URL /booth/2/3/ was not found on this server." in self.driver.page_source

    def test_add_to_census(self):
        self.crear_votacion()

        self.driver.find_element(By.LINK_TEXT, "Votings").click()
        self.driver.find_element(By.ID, "action-toggle").click()
        self.driver.find_element(By.NAME, "action").click()
        dropdown = self.driver.find_element(By.NAME, "action")
        dropdown.find_element(By.XPATH, "//option[. = 'Start']").click()
        self.driver.find_element(By.NAME, "action").click()
        self.driver.find_element(By.NAME, "index").click()

        self.driver.get(f'{self.live_server_url}/admin/census/census/')
        assert '<a href="/admin/census/census/1/change/">1</a>' in self.driver.page_source
    
    def test_stop_voting(self):
        self.crear_votacion()
        self.driver.find_element(By.LINK_TEXT, "Votings").click()
        self.driver.find_element(By.ID, "action-toggle").click()
        self.driver.find_element(By.NAME, "action").click()
        dropdown = self.driver.find_element(By.NAME, "action")
        dropdown.find_element(By.XPATH, "//option[. = 'Start']").click()
        self.driver.find_element(By.NAME, "action").click()
        self.driver.find_element(By.NAME, "index").click()

        self.driver.find_element(By.ID, "action-toggle").click()
        dropdown = self.driver.find_element(By.NAME, "action")
        dropdown.find_element(By.XPATH, "//option[. = 'Stop']").click()
        self.driver.find_element(By.NAME, "action").click() 
        self.driver.find_element(By.NAME, "index").click()

        self.driver.get(f'{self.live_server_url}/admin/voting/voting/1/change/')
        assert str(timezone.now().year) in self.driver.page_source
        assert str(timezone.now().day) in self.driver.page_source


    def test_mensaje_tally(self):
        self.crear_votacion()

        self.driver.find_element(By.LINK_TEXT, "Votings").click()
        self.driver.find_element(By.ID, "action-toggle").click()
        self.driver.find_element(By.NAME, "action").click()
        dropdown = self.driver.find_element(By.NAME, "action")
        dropdown.find_element(By.XPATH, "//option[. = 'Start']").click()
        self.driver.find_element(By.NAME, "action").click()
        self.driver.find_element(By.NAME, "index").click()

        self.driver.get(f'{self.live_server_url}/booth/1/1')
        self.driver.find_element(By.ID, "username").send_keys("admin")
        self.driver.find_element(By.ID, "password").send_keys("qwerty")
        
        self.driver.find_element(By.CSS_SELECTOR    , ".btn-primary").click()
        self.driver.find_element(By.ID, "q1").click()
        self.driver.find_element(By.ID, "voteBtn").click()

        self.driver.get(f'{self.live_server_url}/admin/voting/voting')

        self.driver.find_element(By.ID, "action-toggle").click()
        dropdown = self.driver.find_element(By.NAME, "action")
        dropdown.find_element(By.XPATH, "//option[. = 'Stop']").click()
        self.driver.find_element(By.NAME, "action").click() 

        self.driver.find_element(By.NAME, "index").click()
        self.driver.find_element(By.ID, "action-toggle").click()
        dropdown = self.driver.find_element(By.NAME, "action")
        dropdown.find_element(By.XPATH, "//option[. = 'Tally']").click()
        self.driver.find_element(By.NAME, "action").click()
        self.driver.find_element(By.NAME, "index").click()


    def test_delete_question_of_started_voting(self):
       
       self.driver.get(f'{self.live_server_url}/admin/')
       self.driver.find_element(By.ID, "id_username").send_keys("admin")
       self.driver.find_element(By.ID, "id_password").send_keys("qwerty")
       self.driver.find_element(By.ID, "id_password").send_keys(Keys.ENTER)

       self.driver.find_element(By.CSS_SELECTOR, ".model-auth .addlink").click()
       self.driver.find_element(By.ID, "id_name").send_keys("localhost")
       self.driver.find_element(By.ID, "id_url").send_keys("http://localhost:8000")
       self.driver.find_element(By.NAME, "_save").click()
       self.driver.find_element(By.LINK_TEXT, "Home").click()

       self.driver.find_element(By.CSS_SELECTOR, ".model-question .addlink").click()
       self.driver.find_element(By.ID, "id_desc").send_keys("Pregunta votación")
       self.driver.find_element(By.ID, "id_options-0-number").click()
       self.driver.find_element(By.ID, "id_options-0-number").send_keys("1")
       self.driver.find_element(By.ID, "id_options-0-option").click()
       self.driver.find_element(By.ID, "id_options-0-option").send_keys("A")
       self.driver.find_element(By.ID, "id_options-1-number").click()
       self.driver.find_element(By.ID, "id_options-1-number").send_keys("2")
       self.driver.find_element(By.ID, "id_options-1-option").click()
       self.driver.find_element(By.ID, "id_options-1-option").send_keys("B")
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

       self.driver.find_element(By.LINK_TEXT, "Votings").click() 
       self.driver.find_element(By.ID, "action-toggle").click()
       self.driver.find_element(By.NAME, "action").click()
       dropdown = self.driver.find_element(By.NAME, "action")
       dropdown.find_element(By.XPATH, "//option[. = 'Start']").click()
       self.driver.find_element(By.NAME, "action").click()
       self.driver.find_element(By.NAME, "index").click()
        
       self.driver.find_element(By.LINK_TEXT, "Voting").click()
       self.driver.find_element(By.LINK_TEXT, "Questions").click()

       self.driver.find_element_by_class_name("action-select").click()
       self.driver.find_element_by_name("action").click()
       self.driver.find_element_by_xpath("//*[contains(text(), 'Delete selected')]").click()
       self.driver.find_element_by_class_name("button").click()

       assert self.driver.find_element_by_class_name("error").text == 'This question cannot be deleted because it is part of a started voting'


