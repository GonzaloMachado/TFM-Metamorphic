from django.urls import path

from . import views

app_name = 'metamorphic'
urlpatterns = [
    path('home/', views.DashboardHome.as_view(), name='home'),
    path('dbselector/', views.DBListView.as_view(), name='db_list'),
    path('dbselector/create/', views.DBCreateView.as_view(), name='create_db'),
    path('dbselector/<int:instance_id>/edit/', views.DBUpdateView.as_view(), name='edit_db'),
    path('dbselector/<int:instance_id>/delete/', views.DBDeleteView.as_view(), name='delete_db'),
    path('queries/', views.QueryListView.as_view(), name='query_list'),
    path('queries/create/', views.QueryCreateView.as_view(), name='create_query'),
    path('queries/<int:query_id>/show/', views.QueryTextView.as_view(), name='show_query'),
    path('queries/<int:query_id>/edit/', views.QueryUpdateView.as_view(), name='edit_query'),
    path('queries/<int:query_id>/delete/', views.QueryDeleteView.as_view(), name='delete_query'),
    path('relations/', views.RelationsView.as_view(), name='relations'),
]