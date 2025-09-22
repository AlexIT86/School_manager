from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.inbox_view, name='inbox'),
    path('start/', views.start_conversation_view, name='start'),
    path('<int:convo_id>/', views.conversation_view, name='conversation'),
    path('<int:convo_id>/send/', views.send_message_view, name='send'),
    path('<int:convo_id>/fetch/', views.fetch_messages_view, name='fetch'),
]


