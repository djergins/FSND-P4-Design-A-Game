# -*- coding: utf-8 -*-`
"""api.py - Create and configure the Game API exposing the resources.
This can also contain game logic. For more complex games it would be wise to
move game logic to another file. Ideally the API will be simple, concerned
primarily with communication to/from the API's users."""


import logging
import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import ndb
from models import User, Game 
from models import StringMessage,\
NewGameForm, GameForm, MakeMoveForm, JoinGameForm, GameForms,\
LeaderboardForms
from utils import get_by_urlsafe, get_by_passcode, getUserId  
"""If the request contains path or querystring arguments, you
cannot use a simple Message class. Instead, you must use a 
ResourceContaineClass.""" 
NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
urlsafe_game_key=messages.StringField(1),) 
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(MakeMoveForm,
urlsafe_game_key=messages.StringField(1),) 
JOIN_GAME_REQUEST = endpoints.ResourceContainer(JoinGameForm,
passcode=messages.StringField(1))
CANCEL_GAME_REQUEST = endpoints.ResourceContainer(
urlsafe_game_key=messages.StringField(1),)


MEMCACHE_MOVES_REMAINING = 'MOVES_REMAINING'

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
        current_user = self._getUser()
        users = User.query()
        return LeaderboardForms(items=[user.to_form()\
                         for user in users])

    def _getUser(self):
        """Return user Profile from datastore, creating new one if non-existent."""
        # make sure user is authed
        google_user = endpoints.get_current_user()
        if not google_user:
            raise endpoints.UnauthorizedException('Authorization required')
        logging.info(google_user)
        name = str(google_user)
        email = str(google_user.email())
        

        # get Profile from datastore
        user_id = str(google_user)
        user = User.query(User.name == user_id).get()
        logging.info("user: " + str(user))
        # create new Profile if not there
        if not user:
            logging.info("Making new user!")
            user = User(name=name, email=email,)
            user.put()
        return user      # return Profile

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
                raise endpoints.NotFoundException('A User with that name does not exist!')
            if player2.name == user.name:
                raise endpoints.ConflictException('You are already in the game!')
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
            game = Game.new_game(user.key, board, request.isPlayer1_X, isPlayer1_turn, player2.key)
        else:
            game = Game.new_game(user.key, board, request.isPlayer1_X, isPlayer1_turn)
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
        return GameForms(items=[game.to_form(str(game.key.urlsafe()))\
                         for game in games])

 
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
            if current_user.name == game.player1.get().name or current_user.name == game.player2.get().name:
                if game.isPlayer1_turn:
                    return game.to_form('Game Found! Its your move: ' + game.player1.get().name)
                else:
                    if game.player2:
                        return game.to_form('Game Found! Its your move: ' + game.player2.get().name)
                    else:
                        return game.to_form('Still waiting for second player to join.')   
            else:
                raise endpoints.UnauthorizedException('You are not a member of this game. You cannot pull its details.')
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
        if not game.player2:
            logging.info('Adding player 2')
            player2 = User.query(User.name == current_user.name).get()
            if player2.name == game.player1:
                raise endpoints.ConflictException('You are already in the game!')
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
        player1_number = 1
        player2_number = 2 
        move = 0
        board_full = False

        current_user = self._getUser()
        if request.board < 0 or request.board > 8:
            raise endpoints.ConflictException('You picked an invalid board space!')
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        
        logging.info("player1 is " + game.player1.get().name)
        logging.info("player2 is " + game.player2.get().name)
        if current_user.name != game.player1.get().name and current_user.name != game.player2.get().name:
            raise endpoints.UnauthorizedException("You are not a member of this game.")
        if game.game_over:
            return game.to_form('Game already over!')
        logging.info(request.board)
        if game.isPlayer1_turn and current_user.name == game.player1.get().name:
            move = player1_number
        elif game.isPlayer1_turn == False and current_user.name == game.player2.get().name:
            move = player2_number
        else:
            return game.to_form("It is not your turn, please wait for the other player to move!")
        if game.board[request.board] != 0:
            raise endpoints.ConflictException('You can only update empty spaces!')
        game.board[request.board] = move
        """Pass the turn to the next player before board update."""
        if game.isPlayer1_turn:
            game.isPlayer1_turn = False
        else:
            game.isPlayer1_turn = True

        game.update_board(game.board)
        top_row = [game.board[0],game.board[1],game.board[2]]
        middle_row = [game.board[3],game.board[4],game.board[5]]
        bottom_row = [game.board[6],game.board[7],game.board[8]]
        left_column = [game.board[0],game.board[3],game.board[6]]
        middle_column = [game.board[1],game.board[4],game.board[7]]
        right_column = [game.board[2],game.board[5],game.board[8]]
        left_diagonal = [game.board[0],game.board[4],game.board[8]]
        right_diagonal = [game.board[2],game.board[4],game.board[6]]
        victory_conditions = [top_row, middle_row, bottom_row,\
                              left_column, middle_column, right_column,\
                              left_diagonal, right_diagonal]
        for victory in victory_conditions:
            logging.info(str(victory) + str(victory.count(victory[0]) == len(victory)))
            victory_achieved = victory.count(victory[0]) == len(victory)
            if victory_achieved and victory[0] == 1:
                winner = game.player1.get().name
                game.end_game(winner)
                game.player1.get().gameKeysPlaying.remove(game.key.urlsafe())
                game.player2.get().gameKeysPlaying.remove(game.key.urlsafe())
                game.player1.get().wins += 1
                game.player2.get().losses += 1
                game.player1.get().put()
                game.player2.get().put()
                return game.to_form("Game Over! The winner is: " + winner)
            if victory_achieved and victory[0] == 2:
                winner = game.player2.get().name
                game.end_game(winner)
                game.player1.get().gameKeysPlaying.remove(game.key.urlsafe())
                game.player2.get().gameKeysPlaying.remove(game.key.urlsafe())
                game.player2.get().wins += 1
                game.player1.get().losses += 1
                game.player1.get().put()
                game.player2.get().put()
                return game.to_form("Game Over! The winner is " + winner)

        if all(v != 0 for v in game.board):
            game.end_game(None, True)
            game.player1.get().gameKeysPlaying.remove(game.key.urlsafe())
            game.player2.get().gameKeysPlaying.remove(game.key.urlsafe())
            game.player2.get().draws += 1
            game.player1.get().draws += 1
            game.player1.get().put()
            game.player2.get().put()
            return game.to_form("Draw Game!")
        # TODO:Remove game keys from users now that game is over.
        return game.to_form("Move Made! Next player's move!")

    @endpoints.method(request_message=CANCEL_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/cancel/{urlsafe_game_key}',
                      name='cancel_game')
    def cancel_game(self, request):
        """Cancel a game currently in progress"""
        current_user = self._getUser()
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if current_user.name != game.player1.get().name:
            raise endpoints.UnauthorizedException("You are not a member of this game, you can't cancel it!")
        if game.player2 and current_user.name != game.player2.get().name:
            raise endpoints.UnauthorizedException("You are not a member of this game, you can't cancel it!")
        if game.game_over == True:
            raise endpoints.ConflictException("This game is already over! It can't be cancelled!")
        game.cancelled = True
        game.game_over = True
        game.player1.get().gameKeysPlaying.remove(game.key.urlsafe())
        game.player1.get().put()
        if game.player2:
            game.player2.get().gameKeysPlaying.remove(game.key.urlsafe())
            game.player2.get().put()
        game.put()
        return game.to_form("Game Cancelled!")
        
    @endpoints.method(response_message=StringMessage,
                      path='games/average_attempts',
                      name='get_average_attempts_remaining',
                      http_method='GET')
    def get_average_attempts(self, request):
        """Get the cached average moves remaining"""
        return StringMessage(message=memcache.get(MEMCACHE_MOVES_REMAINING) or '') #Get remaining moves from memcache.

    @staticmethod
    def _cache_average_attempts():
        """Populates memcache with the average moves remaining of Games"""
        games = Game.query(Game.game_over == False).fetch() #games that are not over.
        if games:
            count = len(games)
            total_attempts_remaining = sum([game.attempts_remaining
                                        for game in games])
            average = float(total_attempts_remaining)/count
            memcache.set(MEMCACHE_MOVES_REMAINING,
                         'The average moves remaining is {:.2f}'.format(average))


api = endpoints.api_server([TicTacToeApi])
