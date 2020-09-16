from django.db import models
import random
import json

SPADES = '♠️'
HEARTS = '♥️'
DIAMS = '♦️'
CLUBS = '♣️'
# достоинтсва карт
NOMINALS = ['6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
# поиск индекса по достоинству
NAME_TO_VALUE = {n: i for i, n in enumerate(NOMINALS)}
# карт в руке при раздаче
CARDS_IN_HAND_MAX = 6
N_PLAYERS = 2
# эталонная колода (каждая масть по каждому номиналу) - 36 карт
DECK = [(nom, suit) for nom in NOMINALS for suit in [SPADES, HEARTS, DIAMS, CLUBS]]

def rotate(l, n):
    return l[n:] + l[:n]


class Chat(models.Model):
	external_id = models.PositiveIntegerField(
          verbose_name="Id чата",
          unique=True,
	)
	players_number = models.PositiveIntegerField(
		verbose_name="Колличество играющих",
		)
	deck = models.CharField(max_length=200, default = '0', editable = True)

	def set_deck(self):
		random.shuffle(DECK)
		self.deck = json.dumps(DECK)

	def get_deck(self):
		return json.loads(self.deck)

	trump = models.CharField(max_length = 200, default = '0', editable = True)

	def set_trump(self):
		ideck = self.get_deck()
		self.trump = json.dumps(ideck[0][1])
		ideck = rotate(ideck, -1)
		self.deck = json.dumps(ideck)

	def get_trump(self):
		return json.loads(self.trump)

	attacker_index = models.PositiveIntegerField( default = 0 )
	winner = models.CharField(max_length = 5, default = 'None', editable = True)



	def get_field(self):
		ifield = {}
		for elem in self.field_set.all():
			ikey = json.loads(elem.key)
			ivalue = json.loads(elem.value)
			ifield[tuple(ikey)] = ivalue

		return ifield 

	def set_field(self, dict):
		if dict:
			for elem in dict:
				self.field_set.create(key = json.dumps(elem), value = json.dumps(dict[elem]))
		elif not dict:
			self.field_set.all().delete()
		self.save()


	@property
	def attacking_cards(self):
		"""
		Список атакующих карт
		"""
		ifield = self.get_field()
		return list(filter(bool, ifield.keys()))

	@property
	def last_unbeaten(self):
		"""
		Список атакующих карт
		"""
		ifield = self.get_field()
		for i in ifield:
			if ifield[i] == 'None':
				return i


	@property
	def defending_cards(self):
		"""
		Список отбивающих карт (фильртруем None)
		"""
		ifield = self.get_field()
		return list(filter(bool, ifield.values()))
	@property
	def any_unbeaten_card(self):
		"""
		Есть ли неотбитые карты
		"""
		return any(c is None for c in self.defending_cards)


#Attack:
	@property
	def current_player(self):
		return self.player_set.all()[self.attacker_index]
	@property
	def opponent_player(self):
		return self.player_set.all()[(self.attacker_index + 1) % N_PLAYERS]
	
	@property
	def helper_player(self):
		return self.player_set.all()[(self.attacker_index+2) % N_PLAYERS]


	def attack(self, card):
		assert self.winner == 'None'  # игра не должна быть окончена!
		# можно ли добавить эту карту на поле? (по масти или достоинству)
		if not self.can_add_to_field(card):
			return False
		cur, opp = self.current_player, self.opponent_player
		cur.take_card(card)  # уберем карту из руки атакующего
		ifield = self.get_field()
		ifield[tuple(card)] = 'None'  # карта добавлена на поле, пока не бита
		self.set_field(ifield)
		self.save()
		return True

	def can_add_to_field(self, card):
		ifield = self.get_field()
		if not ifield:  
			# на пустое поле можно ходить любой картой
			return True
		# среди всех атакующих и отбивающих карт ищем совпадения по достоинствам
		
		for attack_card, defend_card in ifield.items():
			if self.card_match(attack_card, card) or self.card_match(defend_card, card):
				return True
		return False

	def card_match(self, card1, card2):
		if card1 is None or card2 is None:
			return False
		n1, _ = card1
		n2, _ = card2
		return n1 == n2   # равны ли достоинства карт?



#Defend
	def defend(self, attacking_card, defending_card):
		"""
		Защита
		:param attacking_card: какую карту отбиваем 
		:param defending_card: какой картой защищаемя
		:return: bool - успех или нет
		"""
		assert self.winner == 'None'  # игра не должна быть окончена!
		ifield = self.get_field()
		print(str(ifield))
		print(str(attacking_card))
		print(attacking_card)
		if ifield[attacking_card] != 'None':
			# если эта карта уже отбита - уходим
			return False
		if self.can_beat(attacking_card, defending_card):
			print("i am here")
			# еслии можем побить, то кладем ее на поле 
			ifield[attacking_card] = defending_card
			self.set_field(ifield)
			# и изымаем из руки защищающегося
			self.opponent_player.take_card(defending_card)
			self.save()
			return True
		return False

	def can_beat(self, card1, card2):
		"""
		Бьет ли card1 карту card2
		"""
		nom1, suit1 = card1
		nom2, suit2 = card2

		# преобразуем строку-достоинство в численные характеристики
		nom1 = NAME_TO_VALUE[nom1]
		nom2 = NAME_TO_VALUE[nom2]

		if suit2 == self.get_trump():
			# если козырь, то бьет любой не козырь или козырь младше
			return suit1 != self.get_trump() or nom2 > nom1
		elif suit1 == suit2:
			# иначе должны совпадать масти и номинал второй карты старше первой
			return nom2 > nom1
		else:
			return False




#Finish Turn

		# константы результатов хода
	NORMAL = 'normal'
	TOOK_CARDS = 'took_cards'
	GAME_OVER = 'game_over'
    
	@property
	def attack_succeed(self):
		ifield = self.get_field()
		return any(def_card == 'None' for def_card in ifield.values())
	
	def finish_turn(self):
		assert self.winner == 'None'
		took_cards = False
		print('attack succeed:')
		print(self.attack_succeed)
		if self.attack_succeed:
			# забрать все карты, если игрок не отбился в момент завершения хода
			self._take_all_field()
			self.save()
			took_cards = True
		else:
			# бито! очищаем поле (отдельного списка для бито нет, просто удаляем карты)
			ifield = self.get_field()
			ifield = {}
			self.set_field(ifield)
			print('field:')
			self.save()
			print(self.get_field())
		# очередность взятия карт из колоды определяется индексом атакующего (можно сдвигать на 1, или нет)
		for p in rotate(list(self.player_set.all()), self.attacker_index):
			ideck = self.get_deck()
			p.take_cards_from_deck(ideck)
			p.save()
		# колода опустела?
		ideck = self.get_deck()
		if not ideck:
			for p in self.player_set.all():
				if not p.get_cards():  # если у кого-то кончились карты, он победил!
					self.winner = list(self.player_set.all()).index(p)
					self.save()
					return self.GAME_OVER
		if took_cards:
			self.save()
			return self.TOOK_CARDS
		else:
			# переход хода, если не отбился
			self.attacker_index = list(self.player_set.all()).index(self.opponent_player)
			self.save()
			return self.NORMAL
	def _take_all_field(self):
		"""
		Соперник берет все катры со стола себе.  
		"""
		print('CARDS IN TAKE aLL FIELD')
		cards = list(self.attacking_cards) + list(self.defending_cards)
		icards = []
		for c in cards:
			print(c)
			if c != 'None':
				icard = list(c)
				icards.append(icard)
		print(self.opponent_player.username)
		print(str(icards))
		self.opponent_player.add_cards(icards)
		self.opponent_player.save()
		ifield = {}
		self.set_field(ifield)


	




	def __str__(self):
		return '%s %s' % (self.external_id, self.players_number)

	class Meta:
		verbose_name = "Чат"
		verbose_name_plural = 'Чаты'

class Field(models.Model):
	container = models.ForeignKey(Chat, db_index=True, on_delete = models.CASCADE)
	key       = models.CharField(max_length=240, db_index=True)
	value     = models.CharField(max_length=240, db_index=True)

class Player(models.Model):
	external_id = models.PositiveIntegerField(
		verbose_name="Id чата",
		unique=True,
	)

	username = models.CharField(max_length=32)

	chats = models.ForeignKey(Chat, on_delete = models.CASCADE)

	cards = models.CharField(max_length = 200, default = '0', editable = True)

	def __str__(self):
		return '%s %s' % (self.external_id, self.username)


	def take_cards_from_deck(self, deck: list):
		"""
		Взять недостающее количество карт из колоды
		Колода уменьшится
		:param deck: список карт колоды 
		"""
		icards = self.get_cards()
		lack = max(0, CARDS_IN_HAND_MAX - len(icards))  
		n = min(len(deck), lack)
		self.add_cards(deck[:n]) 
		del deck[:n]
		self.chats.deck = json.dumps(deck) 
		return self
    
	def sort_hand(self):
		"""
		Сортирует карты по достоинству и масти
		"""
		self.cards = json.dumps(self.get_cards().sort(key=lambda c: (NAME_TO_VALUE[c[0]], c[1])))
		return self
    
	def add_cards(self, cards):
		icards = self.get_cards()
		self.cards = json.dumps(list(icards) + list(cards))
		self.save()
		#self.sort_hand()
		return self

	def get_cards(self):
		icards = json.loads(self.cards)
		if icards == 0:
			icards = []
		return icards

	def __repr__(self):
		return f"Player{self.cards!r}"

	def take_card(self, card):
		icards = self.get_cards()
		icards.remove(card)
		self.cards = json.dumps(list(icards))
		self.save()

	@property
	def n_cards(self):
		icards = self.get_cards()
		return len(icards)

	def __getitem__(self, item):
		icards = self.get_cards()
		return icards[item]

	class Meta:
		verbose_name = "Игрок"
		verbose_name_plural = 'Игроки'