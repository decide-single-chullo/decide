from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.test import APITestCase

from base import mods


class BaseTestCase(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.token = None
        mods.mock_query(self.client)

        user_noadmin = User(username='noadmin', first_name='noadmin', last_name='last_name_noadmin')
        user_noadmin.set_password('qwerty')
        user_noadmin.save()

        user_admin = User(username='admin', is_staff=True,  is_superuser=True, first_name='admin', last_name='last_name_admin') 
        user_admin.set_password('qwerty')
        user_admin.save()

    def tearDown(self):
        self.client = None
        self.token = None

    def login(self, user='admin', password='qwerty'):
        data = {'username': user, 'password': password}
        response = mods.post('authentication/login', json=data, response=True)
        self.assertEqual(response.status_code, 200)
        self.token = response.json().get('token')
        self.assertTrue(self.token)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token)

    def logout(self):
        self.client.credentials()
