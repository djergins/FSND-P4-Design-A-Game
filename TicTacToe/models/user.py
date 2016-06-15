from protorpc import messages
from google.appengine.ext import ndb


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()
    gameKeysPlaying = ndb.StringProperty(repeated=True)
    wins = ndb.IntegerProperty(default=0)
    losses = ndb.IntegerProperty(default=0)
    draws = ndb.IntegerProperty(default=0)

    def to_form(self):
        """Returns form representation
        of User Entity."""
        form = LeaderboardForm()
        form.player = self.name
        form.wins = self.wins
        form.losses = self.losses
        form.draws = self.draws
        return form


class LeaderboardForm(messages.Message):
    """Form for a player's game records."""
    player = messages.StringField(1)
    wins = messages.IntegerField(2)
    losses = messages.IntegerField(3)
    draws = messages.IntegerField(4)


class LeaderboardForms(messages.Message):
    """Multiple players' game records"""
    items = messages.MessageField(LeaderboardForm, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)
