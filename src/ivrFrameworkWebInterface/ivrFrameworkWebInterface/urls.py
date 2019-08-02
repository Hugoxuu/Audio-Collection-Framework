from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('login', views.login_action, name='login'),
    path('logout', views.logout_action, name='logout'),
    path('homepage', views.homepage, name='homepage'),
    path('userManage', views.user_manage_action, name='userManage'),
    path('collectionRequest', views.collection_request_action, name='collectionRequest'),
    path('downloadCallRecordings', views.download_call_recordings, name='downloadCallRecordings'),
    path('transcribeJobRequest', views.transcribe_job_request, name='transcribeJobRequest'),
    path('about', views.about_action, name='about'),
    path('changeCollectionStatus', views.change_collection_status, name='changeCollectionStatus'),
]
