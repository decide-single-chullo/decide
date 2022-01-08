from django.contrib.auth import backends
from django.contrib.auth.models import User

class EmailAuthBackend(backends.ModelBackend):
    """
    Email Authentication Backend
    Permite al usuario autenticarse utilizando su email y contraseña.
    """

    def authenticate(self, username=None, password=None):
        """ Authenticate a user based on email address as the user name. """
        try:
            user = User.objects.get(email=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None