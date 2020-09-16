from django import forms

from .models import Chat, Player


class ChatForm(forms.ModelForm):

	class Meta:
		model = Chat
		fields = (
			'external_id',
			'players_number',
		)


class PlayerForm(forms.ModelForm):

	class Meta:
		model = Player
		fields = (
			'external_id',
			'username',
			'chats',
		)