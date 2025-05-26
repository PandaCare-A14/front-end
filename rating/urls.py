from django.urls import path
from . import views

app_name = 'rating'

urlpatterns = [
    # The rating-list view expects id_pacilian in the URL
    path('rating/list/<uuid:id_pacilian>/', views.RatingListView.as_view(), name='list'),
    path('add/<uuid:consultation_id>/', views.AddRatingView.as_view(), name='add'),
    path('edit/<uuid:consultation_id>/', views.EditRatingView.as_view(), name='edit'),
    path('delete/<uuid:consultation_id>/', views.DeleteRatingView.as_view(), name='delete'),
    path('view/<uuid:consultation_id>/', views.ViewRatingView.as_view(), name='view'),
]
