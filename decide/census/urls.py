from django.urls import path, include
from . import views


urlpatterns = [
    path('', views.CensusCreate.as_view(), name='census_create'),
    path('upload', views.upload_file_view, name='census_upload'), 
    path('<int:voting_id>/', views.CensusDetail.as_view(), name='census_detail'),
]
