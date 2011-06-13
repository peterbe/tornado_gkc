from pprint import pprint
from collections import defaultdict
import datetime
from apps.main.models import BaseDocument, User
from apps.questions.models import Question
from utils import dict_plus

class Play(BaseDocument):
    __collection__ = 'plays'
    structure = {
      'users': [User],

      # consider replacing all of these for just 'rules': dict
      'no_players': int,
      'no_questions': int,

      'halted': datetime.datetime,
      'started': datetime.datetime,
      'finished': datetime.datetime,

      'draw': bool,
      'winner': User
    }

    default_values = {
      'no_players': 0,
      'draw': False,
    }

    def get_other_user(self, this_user):
        return [x for x in self.users if x != this_user][0]


class PlayedQuestion(BaseDocument):
    __collection__ = 'played_questions'
    structure = {
      'play': Play,
      'question': Question,
      'user': User,
      'right': bool,
      'answer': unicode,
      'alternatives': bool,
      'timed_out': bool,
    }

    default_values = {
      'right': False,
      'timed_out': False,
      'alternatives': False,
    }


class PlayMessage(BaseDocument):
    __collection__ = 'play_messages'
    structure = {
      'play': Play,
      'from': User,
      'to': User,
      'message': unicode,
      'read': bool,
    }

    default_values = {
      'read': False,
    }


class PlayPoints(BaseDocument):
    __collection__ = 'play_points'
    structure = {
      'user': User,
      'points': int,
      'wins': int,
      'losses': int,
      'draws': int,
      'highscore_position': int,
    }

    required_fields = ['user','points']

    def update_highscore_position(self):
        pps = (
          self.db.PlayPoints
          .find({'points':{'$gt': 0}})
          .sort('points', -1)
          )
        return_position = None
        position = 0
        _prev_points = -1
        for pp in pps:
            if _prev_points != pp.points:
                position += 1
            if position != pp.highscore_position:
                pp.highscore_position = position
                pp.save()
            if pp == self:
                self.highscore_position = position
            _prev_points = pp.points


    @staticmethod
    def calculate(user):
        db = user.db
        search = {
          'users.$id': user._id,
          'finished': {'$ne': None},
          #'halted': None,
        }
        play_points = db.PlayPoints.one({'user.$id': user._id})
        if not play_points:
            play_points = db.PlayPoints()
            play_points.user = user
        # reset all because we're recalculating
        play_points.points = 0
        play_points.wins = 0
        play_points.losses = 0
        play_points.draws = 0
        for play in db.Play.collection.find(search):
            play = dict_plus(play)
            if play.winner and play.winner.id == user._id:
                play_points.wins += 1
            elif play.draw:
                play_points.draws += 1
            else:
                try:
                    assert play.winner
                    assert play.winner.id != user._id
                except AssertionError:
                    # This happens because of a bug in the game, where a draw
                    # isn't saved properly.
                    print "FIXING"
                    points = defaultdict(int)
                    for u in play.users:
                        for pq in db.PlayedQuestion.find({'play.$id':play._id, 'user.$id':u._id}):
                            if pq.right:
                                if pq.alternatives:
                                    p = 1
                                else:
                                    p = 3
                            else:
                                p = 0
                            points[u.username] += p
                    if sum(points.values()) == 0:
                        for pq in db.PlayedQuestion.find({'play.$id':play._id}):
                            pq.delete()
                        play.delete()
                        continue

                    if len(points) == 2 and len(set(points.values())):
                        play.draw = True
                        play.save()
                        play_points.draws += 1
                        continue

                    print "WINNER", repr(play.winner)
                    print "USERS", [x.username for x in play.users]
                    print "DRAW", repr(play.draw)
                    print "FINISHED", repr(play.finished)
                    print "HALTED", repr(play.halted)
                    print "\n"
                    #pprint(dict(play))
                    continue

                play_points.losses += 1
            #print
            try:
                for played in (user.db.PlayedQuestion.collection
                                 .find({'play.$id': play._id,
                                        'user.$id': user._id})):
                    #pprint(played)
                    played = dict_plus(played)
                    if played.right:
                        if played.alternatives:
                            play_points.points += 1
                        else:
                            play_points.points += 3
            except:
                print "BROKEN!!!"
                print user.username,
                print "Against", play.get_other_user(user).username
                print "PLAY", play._id
                print "USER", user._id
                raise

                return play_points
        play_points.save()
        return play_points
