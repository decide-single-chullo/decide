from django.urls import path
from .views import BoothView
from booth import views as booth_views
from django.views.generic import RedirectView


urlpatterns = [
    #path('<int:voting_id>/', BoothView.as_view()),
    path('<int:voting_id>/<int:question_id>/', booth_views.BoothView.as_view(), name="voting"),
]
