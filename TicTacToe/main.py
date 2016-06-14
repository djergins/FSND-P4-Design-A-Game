#!/usr/bin/env python

"""main.py - This file contains handlers that are called by taskqueue and/or
cronjobs."""
import logging

import webapp2
from google.appengine.api import mail, app_identity
from api import TicTacToeApi

from models import User


class SendReminderEmail(webapp2.RequestHandler):

    def get(self):
        """Send a reminder email to each User with an email and active games.
        Called every 24 hours using a cron job"""
        app_id = app_identity.get_application_id()
        users = User.query(
            User.email is not None and User.gameKeysPlaying is not None)
        for user in users:
            subject = 'This is a reminder!'
            body = """Hello {0}, You currently have active games that you are still playing!\n
                      You are still
                      playing {1} games.""".format(user.name,
                                                   len(user.gameKeysPlaying))
            mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
                           user.email,
                           subject,
                           body)


class UpdateAverageMovesRemaining(webapp2.RequestHandler):

    def post(self):
        """Update game listing announcement in memcache."""
        GuessANumberApi._cache_average_attempts()
        self.response.set_status(204)


app = webapp2.WSGIApplication([
    ('/crons/send_reminder', SendReminderEmail),
], debug=True)
