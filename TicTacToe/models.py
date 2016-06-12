"""models.py - This file contains the class definitions for the Datastore
entities used by the Game. Because these classes are also regular Python
classes they can include methods (such as 'to_form' and 'new_game')."""

import random
import logging
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email =ndb.StringProperty()
    gameKeysPlaying = ndb.StringProperty(repeated=True)
    wins = ndb.IntegerProperty(default=0)
    losses = ndb.IntegerProperty(default=0)
    draws = ndb.IntegerProperty(default=0)

    def to_form(self):
        form = LeaderboardForm()
        form.player = self.name
        form.wins = self.wins
        form.losses = self.losses
        form.draws = self.draws
        return form

class Game(ndb.Model):
    """Game object"""
    # target = ndb.IntegerProperty(required=True)
    # attempts_allowed = ndb.IntegerProperty(required=True)
    # attempts_remaining = ndb.IntegerProperty(required=True, default=5)
    # game_over = ndb.BooleanProperty(required=True, default=False)
    # user = ndb.KeyProperty(required=True, kind='User')

    player1 = ndb.KeyProperty(required=True, kind='User')
    player2 = ndb.KeyProperty(required=False, kind='User')
    board = ndb.IntegerProperty(repeated=True)
    isPlayer1_X = ndb.BooleanProperty(required=True, default=True)
    isPlayer1_turn = ndb.BooleanProperty(required=True, default=True)
    game_over = ndb.BooleanProperty(required=True, default=False)
    winner = ndb.KeyProperty(required=False, kind='User')
    cancelled = ndb.BooleanProperty(required=False, default=False)

    @classmethod
    def new_game(cls, player1, board, isPlayer1_turn, isPlayer1_X, player2=None):
        """Creates and returns a new game"""
        game = Game(player1=player1,
                    isPlayer1_X=isPlayer1_X,
                    board=board,
                    isPlayer1_turn=isPlayer1_turn,
                    player2=player2,
                    game_over=False)
        game.put()
        return game

    def base10toN(self, num, base):
        """Change ``num'' to given base
        Upto base 36 is supported."""

        converted_string, modstring = "", ""
        currentnum = num
        if not 1 < base < 37:
            raise ValueError("base must be between 2 and 36")
        if not num:
            return '0'
        while currentnum:
            mod = currentnum % base
            currentnum = currentnum // base
            converted_string = chr(48 + mod + 7*(mod > 9)) + converted_string
        return converted_string

    def dashify(self, passkey):
        """Throw dashes in the passkey every four characters. For readability."""
        return '-'.join(passkey[i:i+4] for i in
            xrange(0,len(passkey), 4))

    def to_form(self, message):
        """Returns a GameForm representation of the Game"""
        # form = GameForm()
        # form.urlsafe_key = self.key.urlsafe()
        # form.user_name = self.user.get().name
        # form.attempts_remaining = self.attempts_remaining
        # form.game_over = self.game_over
        # form.message = message
        # return form

        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.player1_name = self.player1.get().name
        if self.player2 != None:
            form.player2_name = self.player2.get().name
        form.board = self.board
        form.game_over = self.game_over
        form.isPlayer1_turn = self.isPlayer1_turn
        form.isPlayer1_X = self.isPlayer1_X
        form.message = message
        game_key = self.key.id()
        keyBase36 = self.base10toN(game_key, 36)
        passkey = self.dashify(keyBase36)
        form.passkey = passkey
        form.cancelled = self.cancelled
        if self.winner != None:
            form.winner = self.winner.get().name
        return form

    def end_game(self, winner=None, draw=False):
        """Ends the game - if won is True, the player won. - if won is False,
        the player lost."""
        if winner:
            victor = User.query(User.name == winner).get().key
            self.winner=victor
            self.game_over = True
            self.put()
        if draw:
            self.game_over = True
            self.put()
        # Add the game to the score 'board'

    def join_game(self, player2):
        self.player2 = player2
        self.put()

    def update_board(self, board):
        self.board = board
        self.put()
        
class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    board = messages.IntegerField(2, repeated=True)
    game_over = messages.BooleanField(3, required=True)
    message = messages.StringField(4, required=True)
    player1_name = messages.StringField(5, required=True)
    player2_name = messages.StringField(6, required=False)
    isPlayer1_turn = messages.BooleanField(7, required=True)
    isPlayer1_X = messages.BooleanField(8, required=True)
    passkey = messages.StringField(9, required=True)
    winner = messages.StringField(10, required=False)
    cancelled = messages.BooleanField(11, required=True)

class NewGameForm(messages.Message):
    """Used to create a new game"""
    player2_name = messages.StringField(1, required=False)
    isPlayer1_X = messages.BooleanField(2, required=True)

class JoinGameForm(messages.Message):
    passkey = messages.StringField(1, required=True)
  
class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""
    board = messages.IntegerField(1, required=True)

class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)

class GameForms(messages.Message):
    items = messages.MessageField(GameForm, 1, repeated=True)

class LeaderboardForm(messages.Message):
    player = messages.StringField(1)
    wins = messages.IntegerField(2)
    losses = messages.IntegerField(3)
    draws = messages.IntegerField(4)

class LeaderboardForms(messages.Message):
    items = messages.MessageField(LeaderboardForm, 1, repeated=True)

    
