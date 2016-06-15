# -*- coding: utf-8 -*-`
"""api.py - This file is an extendenable API designed to work with
google app engine. This particular API is for a 2 player game of
Tic-Tac-Toe. More details on the various endpoints and their
expected parameters can be found in README.md"""


import logging
import endpoints
from protorpc import remote, messages
from google.appengine.ext import ndb
from models.game import (Game,
                         NewGameForm,
                         GameForm,
                         MakeMoveForm,
                         JoinGameForm,
                         GameForms,
                         GameHistoryForm)
from models.user import User, StringMessage, LeaderboardForms
from utils import get_by_urlsafe, get_by_passcode
"""If the request contains path or querystring arguments, you
cannot use a simple Message class. Instead, you must use a
ResourceContaineClass."""
NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm, urlsafe_game_key=messages.StringField(1),)
JOIN_GAME_REQUEST = endpoints.ResourceContainer(
    JoinGameForm, passcode=messages.StringField(1))
CANCEL_GAME_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key=messages.StringField(1),)
GAME_HISTORY_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key=messages.StringField(1),)


@endpoints.api(name='tic_tac_toe', version='v1')
class TicTacToeApi(remote.Service):
    """Game API"""
    @endpoints.method(response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        name = str(endpoints.get_current_user())
        email = str(endpoints.get_current_user().email())
        if User.query(User.name == name).get():
            raise endpoints.ConflictException(
                'A User with that name already exists!')
        user = User(name=name, email=email)
        user.put()
        return StringMessage(message='User {} created!'.format(
            name))

    @endpoints.method(response_message=LeaderboardForms,
                      path='user/games/rankings',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        """Return rankings for all users."""
        users = User.query()
        return LeaderboardForms(items=[user.to_form()
                                       for user in users])

    def _getUser(self):
        """Return user Profile from datastore,
        creating new one if non-existent."""
        google_user = endpoints.get_current_user()
        if not google_user:
            raise endpoints.UnauthorizedException('Authorization required')
        logging.info(google_user)
        name = str(google_user)
        email = str(google_user.email())
        user_id = str(google_user)
        user = User.query(User.name == user_id).get()
        logging.info("user: " + str(user))
        if not user:
            logging.info("Making new user!")
            user = User(name=name, email=email,)
            user.put()
        return user

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        user = self._getUser()
        if request.player2_name:
            player2 = User.query(User.name == request.player2_name).get()
            if not player2:
                raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
            # Check that the user isn't playing against themselves.
            if player2.name == user.name:
                raise endpoints.ConflictException(
                    'You are already in the game!')
        else:
            player2 = None
        board = [0] * 9
        'In many instances of tic tac toe, X goes first. House rules.'
        if request.isPlayer1_X:
            isPlayer1_turn = True
        else:
            isPlayer1_turn = False
        if not user:
            raise endpoints.NotFoundException(
                'A User with that name does not exist!')
        if request.player2_name:
            game = Game.new_game(
                user.key,
                board,
                request.isPlayer1_X,
                isPlayer1_turn,
                player2.key)
        else:
            game = Game.new_game(
                user.key,
                board,
                request.isPlayer1_X,
                isPlayer1_turn)
        user.gameKeysPlaying.append(game.key.urlsafe())
        user.put()
        if request.player2_name:
            if game.player2 and game.player1 != game.player2:
                player2.gameKeysPlaying.append(game.key.urlsafe())
                player2.put()
        return game.to_form('Have fun playing Tic-Tac-Toe!')

    @endpoints.method(response_message=GameForms,
                      path='user/games/playing',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Returns all games a user is playing."""
        user = self._getUser()
        game_keys = [ndb.Key(urlsafe=wsgk) for wsgk in user.gameKeysPlaying]
        logging.info("gameKeysPlaying: %s", user.gameKeysPlaying)
        logging.info("game keys: %s", game_keys)
        games = ndb.get_multi(game_keys)
        logging.info("games: %s", games)
        return GameForms(items=[game.to_form(str(game.key.urlsafe()))
                                for game in games])

    @endpoints.method(request_message=GAME_HISTORY_REQUEST,
                      response_message=GameHistoryForm,
                      path='game/history/{urlsafe_game_key}',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """Return the move history of a game."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        return GameHistoryForm(moves=game.history)

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        current_user = self._getUser()
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        logging.info(game)
        logging.info(str(current_user))
        logging.info(game.player1)
        logging.info(game.player2)
        if game:
            if current_user.name == game.player1.get(
            ).name or current_user.name == game.player2.get().name:
                if game.isPlayer1_turn:
                    return game.to_form(
                        'Game Found! Its your move: ' +
                        game.player1.get().name)
                else:
                    if game.player2:
                        return game.to_form(
                            'Game Found! Its your move: ' +
                            game.player2.get().name)
                    else:
                        return game.to_form(
                            'Still waiting for second player to join.')
            else:
                raise endpoints.UnauthorizedException(
                    '''You are not a member of this game.
                    You cannot pull its details.''')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=JOIN_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{passcode}',
                      name='join_game',
                      http_method='PUT')
    def join_game(self, request):
        """Join an existing game."""
        current_user = self._getUser()
        logging.info("_getUser: " + str(current_user))
        game = get_by_passcode(request.passcode, Game)
        if not game:
            raise endpoints.NotFoundException('Game not found!')
        if game.cancelled:
            raise endpoints.ConflictException('Sorry, this game is over!')
        if not game.player2:
            logging.info('Adding player 2')
            player2 = User.query(User.name == current_user.name).get()
            if player2.name == game.player1.get().name:
                raise endpoints.ConflictException(
                    'You are already in the game!')
            game.join_game(player2.key)
            if game.player1 != game.player2:
                player2.gameKeysPlaying.append(game.key.urlsafe())
                player2.put()
            return game.to_form('Welcome to the game!')
        else:
            raise endpoints.ConflictException(
                'Sorry, this game is already in progress!')

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/play/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns a game state with message"""
        current_user = self._getUser()
        if request.board < 0 or request.board > 8:
            raise endpoints.ConflictException(
                'You picked an invalid board space!')
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        move = game.is_move_legal(current_user, request)
        game.board[request.board] = move
        game.update_board(game.board)
        game.update_history(move, request.board)
        game.pass_turn()
        return game.is_victory_achieved()

    @endpoints.method(request_message=CANCEL_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/cancel/{urlsafe_game_key}',
                      name='cancel_game',
                      http_method='PUT')
    def cancel_game(self, request):
        """Cancel a game currently in progress"""
        current_user = self._getUser()
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        logging.info(game.player2)
        if not game.player2:
            if current_user.name != game.player1.get().name:
                raise endpoints.UnauthorizedException(
                    "You are not a member of this game, you can't cancel it!")
        else:
            if current_user.name != game.player1.get().name and\
                    current_user.name != game.player2.get().name:
                raise endpoints.UnauthorizedException(
                    "You are not a member of this game, you can't cancel it!")
        if game.game_over:
            raise endpoints.ConflictException(
                "This game is already over! It can't be cancelled!")
        game.cancelled = True
        game.game_over = True
        game.player1.get().gameKeysPlaying.remove(game.key.urlsafe())
        game.player1.get().put()
        if game.player2:
            game.player2.get().gameKeysPlaying.remove(game.key.urlsafe())
            game.player2.get().put()
        game.put()
        return game.to_form("Game Cancelled!")

api = endpoints.api_server([TicTacToeApi])
