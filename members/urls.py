from django.urls import path
from . import views

app_name = 'members'

urlpatterns = [
    # Member CRUD
    path('', views.member_list, name='list'),
    path('create/', views.member_create, name='create'),
    path('<int:pk>/', views.member_detail, name='detail'),
    path('<int:pk>/edit/', views.member_update, name='update'),
    path('<int:pk>/delete/', views.member_delete, name='delete'),
    path('<int:pk>/transfer/', views.member_transfer_sector, name='transfer_sector'),
    
    # Family CRUD
    path('families/', views.family_list, name='family_list'),
    path('families/create/', views.family_create, name='family_create'),
    path('families/<int:pk>/', views.family_detail, name='family_detail'),
    path('families/<int:pk>/edit/', views.family_update, name='family_update'),
    path('families/<int:pk>/delete/', views.family_delete, name='family_delete'),

    # Sector Management
    path('sectors/', views.sector_list, name='sector_list'),
    path('sectors/create/', views.sector_create, name='sector_create'),
    path('sectors/<int:pk>/', views.sector_detail, name='sector_detail'),
    path('sectors/<int:pk>/edit/', views.sector_update, name='sector_update'),
]