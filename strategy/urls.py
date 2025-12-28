from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('update-item/<int:item_id>/', views.update_item, name='update_item'),
    path('settings/', views.settings_edit, name='settings'),
    path('dividend_stocks', views.devidends, name='dividend_stocks'),
    path('update-dividends/', views.update_dividends, name='update_dividends'),
    path('add_asset/', views.asset_add, name='add_asset'),
    path('delete_asset/<int:pk>/', views.asset_delete, name='delete_asset'),
    path('candidates/', views.candidates, name='candidates'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('get_candidates', views.get_candidates, name="get_candidates")
]
