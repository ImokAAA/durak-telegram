from django.contrib import admin
from .forms import ChatForm, PlayerForm
from .models import Chat, Player


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
	list_display = ('id', 'external_id', 'players_number')   
	form = ChatForm


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
	list_display = ('id', 'external_id', 'username')   
	form = PlayerForm
