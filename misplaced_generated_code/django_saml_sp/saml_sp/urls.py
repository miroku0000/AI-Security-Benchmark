from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("saml/acs/", views.assertion_consumer_service, name="saml_acs"),
]
