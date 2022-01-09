from django.test import TestCase
from django.conf import settings
from django.utils import timezone

from base.tests import BaseTestCase
from voting.models import Voting, Question, QuestionOption
from mixnet.models import Auth
from mixnet.mixcrypt import ElGamal
from mixnet.mixcrypt import MixCrypt

from selenium import webdriver
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

import datetime


# Create your tests here.

class VisualizerTestCase(StaticLiveServerTestCase):
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

# Selenium test for visualazing a non started voting
#     def test_visualize_voting(self):
#         v = self.create_voting("voting1")
#         id = v.__getattribute__('id')
#         response = self.driver.get(f'{self.live_server_url}/visualizer/{id}')
#         assert "Votación no comenzada" in self.driver.page_source


# # Selenium test for visualazing an started voting
#     def test_visualize_started_voting(self):
#         v = self.create_voting("voting2")
#         v.start_date = timezone.now()
#         v.save()
#         id = v.__getattribute__('id')
#         response = self.driver.get(f'{self.live_server_url}/visualizer/{id}')
#         assert "Votación en curso" in self.driver.page_source

# # Selenium test for visualazing a finished voting
#     def test_visualize_finished_voting(self):
#         v = self.create_voting("voting3")
#         v.start_date = timezone.now()
#         v.end_date = timezone.now()
#         v.save()
#         id = v.__getattribute__('id')
#         response = self.driver.get(f'{self.live_server_url}/visualizer/{id}')
#         assert "Resultado" in self.driver.page_source

# # Selenium test for visualazing a tallied voting
#     def test_visualize_tallied_voting(self):
#         v = self.create_voting("voting4")
#         v.start_date = timezone.now()
#         v.end_date = timezone.now()
#         v.tally
#         v.save()
#         id = v.__getattribute__('id')
#         response = self.driver.get(f'{self.live_server_url}/visualizer/{id}')
#         assert "option" in self.driver.page_source

