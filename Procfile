% prepara el repositorio para su despliegue. 
release: sh -c 'USER_MAIL="" && USER_MAIL_PASSWORD="" && export USER_MAIL && export USER_MAIL_PASSWORD && cd decide && python manage.py makemigrations && python manage.py migrate'
% especifica el comando para lanzar Decide
web: sh -c 'cd decide && gunicorn decide.wsgi --log-file -'
