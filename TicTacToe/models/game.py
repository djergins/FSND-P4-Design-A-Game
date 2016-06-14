import random
import logging
import endpoints
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb
from models.user import User


class Game(ndb.Model):
    """Game object"""
    player1 = ndb.KeyProperty(required=True, kind='User')
    player2 = ndb.KeyProperty(required=False, kind='User')
    board = ndb.IntegerProperty(repeated=True)
    isPlayer1_X = ndb.BooleanProperty(required=True, default=True)
    isPlayer1_turn = ndb.BooleanProperty(required=True, default=True)
    game_over = ndb.BooleanProperty(required=True, default=False)
    winner = ndb.KeyProperty(required=False, kind='User')
    cancelled = ndb.BooleanProperty(required=False, default=False)
    history = ndb.StringProperty(repeated=True)

    @classmethod
    def new_game(
            cls,
            player1,
            board,
            isPlayer1_turn,
            isPlayer1_X,
            player2=None):
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
            converted_string = chr(48 + mod + 7 * (mod > 9)) + converted_string
        return converted_string

    def dashify(self, passkey):
        """Throw dashes in the passkey every four characters.
        For readability."""
        return '-'.join(passkey[i:i + 4] for i in
                        xrange(0, len(passkey), 4))

    def to_form(self, message):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.player1_name = self.player1.get().name
        if self.player2 is not None:
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
        if self.winner is not None:
            form.winner = self.winner.get().name
        if self.history is not None:
            form.history = self.history
        return form

    def end_game(self, winner=None, draw=False):
        """Ends the game - sets a winner if there is one,
        sets a draw game if there are no winners."""
        if winner:
            victor = User.query(User.name == winner).get().key
            self.winner = victor
            self.game_over = True
            self.update_history()
            self.put()
        if draw:
            self.game_over = True
            self.put()

    def join_game(self, player2):
        """sets player 2 on a game."""
        self.player2 = player2
        self.put()

    def update_board(self, board):
        """Updates a game's board."""
        self.board = board
        self.put()

    def update_history(self, player=None, board=None):
        """Updates a game's move history."""
        logging.info(player)
        logging.info(board)
        if player is not None and board is not None:
            history_string = "player {0} made a move on tile: {1}".format(
                player, board)
            self.history.append(history_string)
        if self.winner is not None:
            self.history.append(
                "{0} won the game!".format(
                    self.winner.get().name))
        self.put()

    def is_victory_achieved(self):
        """Check if a move triggers a win for both players.
        If no victory, then check for a draw. If no draw,
        make it the next player's turn."""
        # Possible game victories.
        top_row = [self.board[0], self.board[1], self.board[2]]
        middle_row = [self.board[3], self.board[4], self.board[5]]
        bottom_row = [self.board[6], self.board[7], self.board[8]]
        left_column = [self.board[0], self.board[3], self.board[6]]
        middle_column = [self.board[1], self.board[4], self.board[7]]
        right_column = [self.board[2], self.board[5], self.board[8]]
        left_diagonal = [self.board[0], self.board[4], self.board[8]]
        right_diagonal = [self.board[2], self.board[4], self.board[6]]
        victory_conditions = [top_row, middle_row, bottom_row,
                              left_column, middle_column, right_column,
                              left_diagonal, right_diagonal]
        # Loop through possible victories.
        for victory in victory_conditions:
            logging.info(str(victory) +
                         str(victory.count(victory[0]) == len(victory)))
            victory_achieved = victory.count(victory[0]) == len(victory)
            # Check if player one won and update Game and User accordingly.
            if victory_achieved and victory[0] == 1:
                winner = self.player1.get().name
                self.end_game(winner)
                self.player1.get().gameKeysPlaying.remove(self.key.urlsafe())
                self.player2.get().gameKeysPlaying.remove(self.key.urlsafe())
                self.player1.get().wins += 1
                self.player2.get().losses += 1
                self.player1.get().put()
                self.player2.get().put()
                return self.to_form("Game Over! The winner is: " + winner)
            # Check if player two won and update Game and User accordingly.
            if victory_achieved and victory[0] == 2:
                winner = self.player2.get().name
                self.end_game(winner)
                self.player1.get().gameKeysPlaying.remove(self.key.urlsafe())
                self.player2.get().gameKeysPlaying.remove(self.key.urlsafe())
                self.player2.get().wins += 1
                self.player1.get().losses += 1
                self.player1.get().put()
                self.player2.get().put()
                return self.to_form("Game Over! The winner is " + winner)
            # Check if game is a draw. Update Game and User accordingly.
            if all(v != 0 for v in self.board):
                self.end_game(None, True)
                self.player1.get().gameKeysPlaying.remove(self.key.urlsafe())
                self.player2.get().gameKeysPlaying.remove(self.key.urlsafe())
                self.player2.get().draws += 1
                self.player1.get().draws += 1
                self.player1.get().put()
                self.player2.get().put()
                return self.to_form("Draw Game!")
        return self.to_form("Move Made! Next player's move!")

    def pass_turn(self):
        """Make it the next player's turn."""
        if self.isPlayer1_turn:
            self.isPlayer1_turn = False
        else:
            self.isPlayer1_turn = True
        self.put()

    def is_move_legal(self, current_user, request):
        """validates that a move is legal and returns a move if it is."""
        player1_number = 1
        player2_number = 2
        move = 0
        if self.player2 is None:
            raise endpoints.ConflictException("Please wait for a second " +
                                              "player to join before " +
                                              "making a move.")
        if current_user.name != self.player1.get(
        ).name and current_user.name != self.player2.get().name:
            raise endpoints.UnauthorizedException(
                "You are not a member of this game.")
        if self.game_over:
            raise endpoints.ConflictException('Game already over!')
        if self.isPlayer1_turn and current_user.name == \
            self.player1.get().name:
            move = player1_number
        elif self.isPlayer1_turn is False and current_user.name == \
            self.player2.get().name:
            move = player2_number
        else:
            raise endpoints.ConflictException(
                "It is not your turn, " +
                "please wait for the other player to move!")
        if self.board[request.board] != 0:
            raise endpoints.ConflictException(
                'You can only update empty spaces!')
        return move


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
    history = messages.StringField(12, repeated=True)


class NewGameForm(messages.Message):
    """Used to create a new game"""
    player2_name = messages.StringField(1, required=False)
    isPlayer1_X = messages.BooleanField(2, required=True)


class JoinGameForm(messages.Message):
    """Join a game with a valid passkey"""
    passkey = messages.StringField(1, required=True)


class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""
    board = messages.IntegerField(1, required=True)


class GameForms(messages.Message):
    """Returns multiple game forms"""
    items = messages.MessageField(GameForm, 1, repeated=True)


class GameHistoryForm(messages.Message):
    """Used to return a game's move history."""
    moves = messages.StringField(1, repeated=True)
