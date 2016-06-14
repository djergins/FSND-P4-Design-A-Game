#Full Stack Nanodegree Project 4 Refresh

## Set-Up Instructions:
1.  Update the value of application in app.yaml to the app ID you have registered
 in the App Engine admin console and would like to use to host your instance of this sample.
1.  Run the app with the devserver using dev_appserver.py DIR, and ensure it's
 running by visiting the API Explorer - by default localhost:8080/_ah/api/explorer.
1.  (Optional) Generate your client library(ies) with the endpoints tool.
 Deploy your application.
 
 
 
##Game Description:
Tic-Tac-Toe is a two player game. This game is won by one of the players successfully filling a sequence of 3 tiles with their symbol, an X or an O. Victory can be achieved horizontally, vertically, and diagonally on the 3x3 game grid. Thus the goal is to fill 3 tiles in a row with your symbol while blocking the other player from filling their 3 tiles in a row. Moves are sent to the 'make_move' enpoint which will check for a winner each round and reply with the following:
"Game Over! The winner is: " + winner, "Draw Game!", or "Move Made! Next player's move!" If a move does not produce a winner or a draw game, it will be the next player's turn. Many different Tic-Tac-Toe games can be played by many different Users at any
given time. Each game can be retrieved or played by using the path parameter `urlsafe_game_key`.

##Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration.
 - main.py: Handler for taskqueue handler.
 - models.__init__.py: init the models folder as a module.
 - models.game.py: Entity and message definitions including helper methods for Game objectsd.
 - models.user.py: Entity and message definitions including helper methods for User objectsd.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.

##Endpoints Included:
 - **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: None, provided by oauth.
    - Returns: Message confirming creation of the User.
    - Description: Creates a new User. user_name provided must be unique. Will 
    raise a ConflictException if a User with that user_name already exists. User credentials provided by oauth google login.

 - **get_user_rankings**
    - Path: 'user/games/rankings'
    - Method: GET
    - Parameters: None
    - Returns: LeaderboardForms detailing each user's name, losses, draws, and wins.
    - Description: Returns a list of all users' game records.
    
 - **new_game**
    - Path: 'game'
    - Method: POST
    - Parameters: player2_name, isPlayer1_X
    - Returns: GameForm with initial game state.
    - Description: Creates a new Game. user_name provided must correspond to an
    existing user - will raise a NotFoundException if not. Will check to make sure that player2 is not player1. Will raise a conflict exception if so. We don't want users racking up a large win record against themselves. 

 - **get_user_games**
    - Path: 'user/games/playing'
    - Method: GET
    - Parameters: None, user provided by oauth.
    - Returns: GameForms with the game state of all of a user's active games. 
    - Description: Returns all of a user's active games as multiple GameForms. These are all games where game_over is not true.

 - **get_game_history**
    - Path: 'game/history/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameHistoryForm with all the moves made thus far in a game.
    - Description: Returns all of a games moves on the game board and which player made the move. If the game has a winner, the winner's name will be returned.
     
 - **get_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Returns the current state of a game. Also returns a message stating which player's turn it is. If the current user is not a member of the game, an UnauthorizedException will prevent them from pulling game details.

 - **join_game**
    - Path: 'game/{passcode}'
    - Method: PUT
    - Parameters: passcode
    - Returns: GameForm with the added 2nd player. 
    - Description: When a game is created, a passcode is generated. This passcode can be sent to others to join a game that still needs a second player. If a game is not found with the given passcode, a NotFoundException is generated. If the player2 name matches the player1 name already in the game, a ConflictException is raised. If there is already a second player in the game, a ConflictException is raised. If the game has been canceled, a conflict exception is raised.
    
 - **make_move**
    - Path: 'game/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key, board
    - Returns: GameForm with new game state.
    - Description: Accepts a 'move' and returns the updated state of the game. A ConflictException is generated if a move is made that is not on the game board, move < 0 or move > 8. If the current user is not a member of the game, an UnauthorizedException is generated. If there is no second player in the game at the time of a move, a ConflictException is thrown instructing the game's creator to wait for a second player. If the game is already over, a ConflictException is generated. If it is not the current user's move, a ConflictException is returned to the user letting them know that it is not their turn to move yet. If the user tries to update a board space that is not empty, not zero, a ConflictException is raised. If victory is achieved, game_over is set to true and the gamekey is removed from both players' activeGameKeysPlaying.
    
 - **cancel_game**
    - Path: 'game/cancel/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key
    - Returns: GameForm with updated state. game_over and cancelled is set to true.
    - Description: Returns a GameForm with cancelled and game_over set to true. Removes gamekey from both players' gameKeysPlaying attribute. If the current user is not player1 or player2, then an UnauthorizedException is raised preventing the cancellation of the game. If the game is already over, then a ConflictException is raised because there is no point in cancelling a game that is already cancelled.

##Models Included:
 - **User**
    - Stores unique user_name and (optional) email address.
    
 - **Game**
    - Stores unique game states. Associated with User model via KeyProperty.
    
##Forms Included:
 - **GameForm**
    - Representation of a Game's state (urlsafe_key, board, game_over, message, player1_name, player2_name, isPlayer1_turn, isPlayer1_X, passkey, winner, cancelled, history).
 - **NewGameForm**
    - Used to create a new game (player2_name, isPlayer1_X).
 - **JoinGameForm**
    - Used to join an existing game (passkey).
 - **MakeMoveForm**
    - Inbound make move form (board).
 - **StringMessage**
    - General purpose String container.
 - **GameForms**
    - Form containing multiple GameForm entity representations (items).
 - **GameHistoryForm**
    - Form for displaying the history of a specific game (moves).
 - **LeaderboardForm**
    - Form containing win, loss, and draw records for one user (player, wins, losses, draws).
 - **LeaderboardForms**
    - Form containing multiple LeaderboardForm entity representations (items).