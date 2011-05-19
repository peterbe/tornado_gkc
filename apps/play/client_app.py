import time
import os.path as op
import logging
import random
from pymongo.objectid import InvalidId, ObjectId
import tornado.web
import tornadio.router
from apps.main.models import User
from apps.play.battle import Battle
from apps.questions.models import Question, Genre
from apps.play.models import Play, PlayedQuestion
from mongokit import Connection
from cookies import CookieParser
import settings

class Client(tornadio.SocketConnection):

    def __repr__(self):
        try:
            info = repr(self.user_name)
        except AttributeError:
            try:
                info = self.user_id
            except AttributeError:
                info = '*unknown*'
        return "<Client: %s %s>" % (self._protocol.__class__.__name__, info)

    @property
    def db(self):
        return application.db

    @property
    def battles(self):
        return application.battles

    @property
    def current_client_battles(self):
        return application.current_client_battles

    @property
    def application_settings(self):
        return application.settings

    def on_open(self, request, **kwargs):
        print "Opening", repr(self)
        self.send({'debug': "Connected!"});
        if not hasattr(request, 'headers'):
            self.send({'error': 'Unable to find login information. Try reloading'})
            return

        cookie_parser = CookieParser(request)
        user_id = cookie_parser.get_secure_cookie('user')

        if not user_id:
            self.send({'error': 'Unable to log you in. Try reloading'})
            return

        self.user_id = user_id
        user = self.db.User.one({'_id': ObjectId(user_id)})
        if user:
            assert user.username
            self.user_name = user.username
            self.send({'debug': "Your name is %s" % self.user_name})
            self._initiate()



    def _initiate(self):
        """called when the client has connected successfully"""
        print "\tInitiate", repr(self)
        self.send(dict(your_name=self.user_name))
        battle = None
        for created_battle in self.battles:
            if created_battle.is_open():
                battle = created_battle
                logging.debug("Joining battle: %r" % battle)
                break
        if not battle:
            battle = Battle(15, # specify how long the waiting delay is
                            no_questions=self.application_settings['debug'] and 5 or 10
                            )
            logging.debug("Creating new battle")
            self.battles.add(battle)
        battle.add_participant(self)
        self.current_client_battles[self.user_id] = battle
        if battle.ready_to_play():
            battle.send_to_all({
              'init_scoreboard': [x.user_name for x in battle.participants]
            })
            battle.send_wait(3, dict(next_question=True))

    def on_message(self, message):
        #print "MESSAGE",
        #print repr(message)
        #print
        if not hasattr(self, 'user_id'):
            print "DUFF client"
            return
        try:
            battle = self.current_client_battles[self.user_id]
        except KeyError:
            logging.debug('%r not in any battle' % self)
            print "No battle :("
            return

        if message.get('answer'):
            if not battle.current_question:
                # form submitted too late
                return
            if battle.has_answered(self):
                self.send({'error': 'You have already answered this question'})
                return
            battle.remember_answered(self)
            if battle.check_answer(message.get('answer')):
                # client got it right!!
                points = 3
                if battle.has_loaded_alternatives(self):
                    points = 1
                self.send({'answered': {'right': True}})
                battle.send_to_everyone_else(self,
                                             {'answered': {'too_slow': True}})
                battle.increment_score(self, points)
                battle.close_current_question()
                if battle.has_more_questions():
                    battle.send_wait(3, dict(next_question=True))
                else:
                    battle.conclude()
            else:
                # you suck!
                self.send({'answered': {'right': False}})
                battle.send_to_everyone_else(self,
                  {'has_answered': self.user_name}
                )
                if battle.has_everyone_answered():
                    battle.close_current_question()
                    battle.send_to_all({'answered':{'both_wrong': True}})
                    if battle.has_more_questions():
                        battle.send_wait(3, dict(next_question=True))
                    else:
                        battle.conclude()

        elif message.get('alternatives'):
            assert battle.current_question
            if not battle.has_loaded_alternatives(self):
                battle.send_alternatives(self)
        elif message.get('timed_out'):
            print "Timed out!", repr(self)
            if not battle.current_question:
                # most likely
                assert battle.is_waiting()
                return
            if battle.timed_out_too_soon():
                print "current_question:", repr(battle.current_question.text)
                logging.warning("time.time():%s current_question_sent+thinking_time:%s"
                                % (time.time(),
                                battle.current_question_sent+battle.thinking_time))
                self.send({'error': 'Timed out too soon'})
                return

            battle.remember_timed_out(self)
            print "battle.timed_out"
            print battle.timed_out
            if battle.has_all_timed_out():
                print "\tALL HAVE TIMED OUT"
                #print battle.timed_out
                #print battle.participants
                print "\n"
                for participant in battle.participants:
                    if not battle.has_answered(participant):
                        participant.send({'answered': {'too_slow': True}})
                print "\t\tCLOSING CURRENT QUESTION"
                battle.close_current_question()
                print "\t\tHas more?", battle.has_more_questions()
                if battle.has_more_questions():
                    print "\t\t\tSending a wait"
                    battle.send_wait(3, dict(next_question=True))
                else:
                    print "\t\t\tConcluding!"
                    battle.conclude()
            else:
                print "\tStill waiting for more to time out"

        elif message.get('next_question'):
            # this is going to be hit twice, within nanoseconds of each other.
            #print (battle.min_wait_delay, time.time())
            if battle.min_wait_delay > time.time():
                self.send({'error': 'Too soon'})
                return
            if battle.stopped:
                #self.send({'error': 'Battle already stopped'})
                return
            if not battle.current_question:
                question = self._get_next_question(battle)
                if question:
                    battle.current_question = question
                    battle.send_question(battle.current_question)
                else:
                    battle.send_to_all({'error':"No more questions! Run out!"})
                    battle.stop()
        else:
            print message
            raise NotImplementedError("Unrecognized message")

    def _get_next_question(self, battle):
        search = {'state': 'PUBLISHED',
                  '_id':{'$nin': [x._id for x in battle.sent_questions]}}
        if battle.genres_only:
            search['genre.$id'] = {'$nin': [x._id for x in battle.genres_only]}

        while True:
            count = self.db.Question.find(search).count()
            if not count:
                return
            rand = random.randint(0, count)
            for question in self.db.Question.find(search).limit(1).skip(rand):
                # XXX at this point we might want to check that the question
                # hasn't been
                #   a) written by any of the participants of the battle
                #   b) hasn't been reviewed by any of the participants
                #   c) questions played in the past
                if 1: # too few questions in db for this at the moment
                    return question
                else:
                    search['_id']['$nin'].append(question._id)

    def on_close(self):
        print repr(self), "closed connection"
        if getattr(self, 'user_id', None) and getattr(self, 'user_name', None):
            try:
                battle = self.current_client_battles[self.user_id]
                print "found battle"
            except KeyError:
                print "cound't find battle"
                logging.debug('%r not in any battle' % self.user_id)
                return

            battle.remove_participant(self)
            battle.send_to_all({'disconnected': self.user_name})
            print "Stopping battle because", self.user_name, "disconnected"
            battle.stop()


class Application(tornado.web.Application):
    battles = set()
    current_client_battles = {}

    def __init__(self, database_name, **kwargs):
        handlers = [tornadio.get_router(Client).route()]
        tornado.web.Application.__init__(self, handlers, **kwargs)
        self.database_name = database_name
        self.con = Connection()
        self.con.register([User, Question, Genre, Play, PlayedQuestion])

    @property
    def db(self):
        return self.con[self.database_name]


HERE = op.normpath(op.dirname(__file__))
from tornado.options import options
application = Application(
      database_name=options.database_name,
      debug=options.debug,
      enabled_protocols=['websocket',
                         'flashsocket',
                         'xhr-multipart',
                         'xhr-polling'
                         ],
      flash_policy_port=843,
      flash_policy_file=op.join(HERE, 'flashpolicy.xml'),
      socket_io_port=options.port,
    )
