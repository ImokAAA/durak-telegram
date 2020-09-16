from django.shortcuts import render
from django.http import HttpResponse
from django.core.management.base import BaseCommand
from django.conf import settings
from telegram import Bot
from telegram.ext import Dispatcher
from telegram import Update
from telegram import KeyboardButton 
from telegram import ReplyKeyboardMarkup
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater
from telegram.ext import ConversationHandler
from telegram.ext import CallbackQueryHandler
from telegram.ext import BaseFilter
from telegram.utils.request import Request
from telegram.utils import helpers
import datetime
import json
from game.models import Chat,Player
from django.db import IntegrityError

START, MOVE, VICTORY, PLAYERS = range(4)

def get_keyboard(cards):
	if cards == '0':
		keyboard = [
			[KeyboardButton(' ')],
		]
	elif cards == []:
		keyboard = [
			[KeyboardButton(' '),],
		]
	else: 
		keyboard = [

    	
		[KeyboardButton(str(card[0])+' '+str(card[1])) for card in cards],
		[KeyboardButton('Бито')],
		]
	return ReplyKeyboardMarkup(keyboard = keyboard,
		resize_keyboard=True,)



bot = Bot(settings.TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

def web_hook_view(request):
	if request.method == 'POST':
		dispatcher.process_update(Update.de_json(json.loads(request.body), bot))
		return HttpResponse(status=200)
	return HttpResponse('404 not found')

updater = Updater(
	token=settings.TOKEN,
	use_context=True
)

def durak(bot: Bot, update:Update):
	chat_id = update.message.chat_id
	gchat, _ = Chat.objects.get_or_create(
		external_id = chat_id,
		defaults={'players_number': 0,
		'attacker_index': 0,
		'winner': 'None',
		},  
	)
	current_chat = update.message.chat_id
	gplayer, _ = Player.objects.get_or_create(
		external_id = current_chat,
		defaults={'username': update.message.chat.first_name,
					'chats': gchat,
					},  
	)
	gchat.players_number = 1
	gchat.save()
	gplayer.save()

	url = helpers.create_deep_linked_url(bot.get_me().username, str(chat_id))
	text = "Новая игра! Чтобы добавить друзей, они должны перейти к ссылке. Перешли эту ссылку на группы или лс твоих друзей. После, набери команду '/startdurak':\n\n" + url
	update.message.reply_text(text)

	return PLAYERS

def start(bot: Bot, update: Update):
	update.message.reply_text(text="I'm a bot, please talk to me!")

def deep_link(bot: Bot, update:Update):
	gamechatid = update.message.text.split()[1]
	current_chatid = update.effective_message.chat_id 
	gchat = Chat.objects.get(external_id=gamechatid)


	eplayer = gchat.player_set.filter(external_id = current_chatid)
	if eplayer:
		bot.send_message(chat_id = update.effective_message.chat_id, text = 'Вы уже в игре!')
	else:
			if gchat.players_number>6:
				bot.send_message(chat_id = gchat.external_id, text = 'Больше 6 людей нельзя добавить. Скорее начните игру')
				bot.send_message(chat_id = update.effective_message.chat_id, text = 'Извините, комната заполнена(')
			else:
				gplayer, _ = Player.objects.get_or_create(
					external_id = current_chatid,
					username = update.message.chat.first_name,
					defaults={'chats' : gchat}
				)
				gplayer.save()
				for player in gchat.player_set.all():
					warning = str(gplayer.username) + " "+"присоединился..."			
					bot.send_message(chat_id = player.external_id, text = warning)
				gchat.players_number += 1
				gchat.save()
				
				text = "Добро пожаловать " + gplayer.username
				bot.send_message(chat_id = update.effective_message.chat_id, text = text)
				return MOVE

def durak_start(bot: Bot, update:Update):
	gplayer = Player.objects.filter(chats__external_id=update.message.chat_id)
	gchat = gplayer[0].chats
	gchat.set_deck()
	gchat.save()
	player_board = 'Игроки:' + '\n'
	for player in gchat.player_set.all():
			deck = gchat.get_deck()
			player.take_cards_from_deck(deck)
			player.save()
			player_board += str(player.id) + '. ' + str(player.username) + " - " +str(player.get_cards()) + '/n'   
	gchat.set_trump()
	gchat.save()
	for player in gchat.player_set.all():
			text = 'Начинаем игру! \n' \
			'Козырь: ' + str(gchat.get_trump()) + '\n' \
			'Остальная колода:' + str(len(gchat.get_deck())) + '\n'+ str(player_board)
			
			bot.send_message(chat_id = player.external_id, text = text, reply_markup = get_keyboard(player.get_cards()))
	
	bot.send_message(chat_id = gchat.player_set.all()[gchat.attacker_index].external_id, text = 'Твой Ход')
	return MOVE


def move(bot: Bot, update:Update):
	#gplayer = Player.objects.filter(chats__external_id=update.message.chat_id)
	chat_id = update.message.chat_id
	g = Chat.objects.filter(player__external_id = chat_id)
	g = g[0]
	#print('gplayer:')
	#print(gplayer)
	#g = gplayer[0].chats
	# разбиваем на части: команда - пробел - номер карты
	parts = update.message.text.split(' ')
	print(parts)
	command = parts[0]
	print('current player id')
	print(g.current_player.external_id)
	print(type(g.current_player.external_id))
	print('chat id')
	print(chat_id)
	print(type(chat_id))
	print(parts in g.current_player.get_cards())
	attacker_moved = parts in g.current_player.get_cards()


	try:

			if command == 'Бито':
				r = g.finish_turn()
				text = "Ход окончен " + str(r)
				for player in g.player_set.all():
							print('player.username')
							print(player.username)
							print('player.get_cards():')
							print(str(player.get_cards()))						
							bot.send_message(chat_id = player.external_id, text = text, reply_markup = get_keyboard(player.get_cards()))
				bot.send_message(chat_id = g.current_player.external_id, text = 'Твой Ход')
			
			elif g.current_player.external_id == chat_id:
				if not parts in g.current_player.get_cards():
					bot.send_message(chat_id = update.effective_message.chat_id, text = "У вас нет такой карты")
				else:
					#index = int(parts[1]) - 1
					#cards = list(g.current_player.get_cards())
					#card = cards[index]
					attack_happened = g.attack(parts) 
					g.save()
					if not attack_happened:
						bot.send_message(chat_id = update.effective_message.chat_id, text = "Вы не можете ходить")
					elif attack_happened:
						field = g.get_field()
						for pair in field:
							ifield = str(pair) + " " + str(field[pair]) + "|"
						text = str(g.current_player.username) + ' сделал Ход \n' \
								'Козырь: ' + str(g.get_trump()) + '\n' \
								'Осталось карт:' + str(len(g.get_deck())) + '\n'\
								'Колода: \n' + str(field)

						for player in g.player_set.all():
							print('player.username')
							print(player.username)
							print('player.get_cards():')
							print(str(player.get_cards()))						
							bot.send_message(chat_id = player.external_id, text = text, reply_markup = get_keyboard(player.get_cards()))
					
			elif g.opponent_player.external_id == chat_id:
				if not parts in g.opponent_player.get_cards():
					bot.send_message(chat_id = update.effective_message.chat_id, text = "У вас нет данной карты")
				else:
					#index = int(parts[1]) - 1
					#new_card = g.opponent_player[index]
					new_card = parts
				# варианты защиты выбранной картой
				#variants = g.defend_variants(new_card)
				#if len(variants) == 1:
				#	def_index = variants[0]
				#else:
				#	def_index = int(input(f'Какую позицию отбить {new_card}? ')) - 1
					#old_card = list(g.attacking_cards)[0]
					old_card = g.last_unbeaten
					defended = g.defend(old_card, new_card)
					if not defended:
						print('Не можете так отбиться')
					elif defended:
						field = g.get_field()
						for pair in field:
							ifield = str(pair) + " " + str(field[pair]) + "|"
						text = str(g.current_player.username) + ' сделал Ход \n' \
								'Козырь: ' + str(g.get_trump()) + '\n' \
								'Осталось карт:' + str(len(g.get_deck())) + '\n'\
								'Колода: \n' + str(field)

						for player in g.player_set.all():
							print('player.username')
							print(player.username)
							print('player.get_cards():')
							print(str(player.get_cards()))						
							bot.send_message(chat_id = player.external_id, text = text, reply_markup = get_keyboard(player.get_cards()))

			elif command == 'q':
				print('QUIT!')
	except IndexError:
			print('Неправильный выбор карты')
	if g.winner != 'None':
			print(f'Игра окончена, победитель игрок: ')
			

def durak_cancel(bot: Bot, update:Update):
	gplayer = Player.objects.filter(chats__external_id=update.message.chat_id)
	gchat = gplayer[0].chats
	if gplayer[0].external_id != gchat.external_id:
		gchat.player_set.delete(gplayer)
		gchat.save()
		bot.send_message(chat_id = update.effective_message.chat_id, text = 'canceled')
	elif gplayer[0].external_id == gchat.external_id:
		gchat.delete()
		gchat.save()
		bot.send_message(chat_id = update.effective_message.chat_id, text = 'canceled')
	return ConversationHandler.END

class FilterDeeplink(BaseFilter):
		def filter(self, message):
			k = message.text
			f = k.split()
			return message.entities[0].type =='bot_command' and f[0] == '/start' and len(f) == 2 


filter_deeplink = FilterDeeplink()

class FilterStart(BaseFilter):
		def filter(self, message):
			k = message.text
			f = k.split()
			return message.entities[0].type == 'bot_command' and f[0] == '/start' and len(f) == 1 
		


filter_start = FilterStart()



durak_conv_handler = ConversationHandler(
				entry_points=[
						CommandHandler('durak', durak ),
						MessageHandler(filter_deeplink, deep_link),
					],
				states={
				PLAYERS: [
					CommandHandler('startdurak', durak_start),
					MessageHandler(filter_deeplink, deep_link),
				],
				MOVE: [
					MessageHandler(Filters.text, move)	
				],
				},
				fallbacks=[
					CommandHandler('cancel', durak_cancel ),
				],
				)
dispatcher.add_handler(durak_conv_handler)
start_handler = MessageHandler(filter_start , start)
dispatcher.add_handler(start_handler)






