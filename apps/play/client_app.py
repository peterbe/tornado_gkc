import datetime
import time
import os.path as op
import logging
import random
from bson.objectid import ObjectId
import tornado.web
import tornadio.router

from apps.main.models import connection
#import apps.main.models
#import apps.questions.models
#import apps.play.models
#import apps.rules.models

from apps.play.battle import Battle
from apps.play import errors
from mongokit import MultipleResultsFound
from cookies import CookieParser

import settings

from bot import ComputerClient

class Client(tornadio.SocketConnection):
    is_bot = False

    def send(self, *args, **kwargs):
        #print "--->", args
        super(Client, self).send(*args, **kwargs)

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
        if self.application_settings['debug']:
            self.send({'debug': "Connected!"});
        if not hasattr(request, 'headers'):
            logging.debug("No headers :(")
            self.send(dict(error={'message': 'Unable to find login information. Try reloading',
                                  'code': errors.ERROR_NOT_LOGGED_IN}))
            return
        cookie_parser = CookieParser(request)
        user_id = cookie_parser.get_secure_cookie('user')
        rules = cookie_parser.get_secure_cookie('rules')

        if rules:
            rules = self.db.Rules.collection.one({'_id': ObjectId(rules)})
        if not rules:
            rules = self.db.Rules.collection.one({'default': True})
            if not rules:
                rules = self.db.Rules()
                rules.no_questions = 10
                rules.thinking_time = 10
                rules.genres = []
                rules.default = True
                rules.save()
                rules = dict(rules)

        if not user_id:
            logging.debug(
              "No secure user_id (cookie_parser.get_cookie('user')=%r)" %
              cookie_parser.get_cookie('user')
            )
            self.send({'error': 'Unable to log you in. Try reloading'})
            return

        self.user_id = user_id
        user = self.db.User.one({'_id': ObjectId(user_id)})
        if not user:
            logging.debug(
              "No user by that id %r" % user_id
            )
            self.send({'error': 'Unable to find your user account. Try reloading.'})
            return

        assert user.username
        self.user_name = user.username
        if self.application_settings['debug']:
            self.send({'debug': "Your name is %s" % self.user_name})
        self._initiate(rules)

    def _initiate(self, rules):
        """called when the client has connected successfully"""
        self.send(dict(your_name=self.user_name))
        battle = None

        _del_battles = set()
        for created_battle in self.battles:
            if created_battle.is_dead(10):
                _del_battles.add(created_battle)
                continue

            if created_battle.is_open(rules):
                if self in created_battle:
                    self.send(dict(error={'message':'Already in an open battle',
                                          'code': errors.ERROR_ALREADY_IN_OPEN_BATTLE}))
                    return
                battle = created_battle
                logging.debug("%r joining battle: %r" % (self.user_name, battle))
                break

        for bad_battle in _del_battles:
            self.battles.remove(bad_battle)

        if not battle:
            battle = Battle(rules)
            logging.debug("Creating new battle")
            self.battles.add(battle)
        battle.add_participant(self, rules)
        self.current_client_battles[self.user_id] = battle
        if battle.ready_to_play():
            battle.commence(self.db)

    def on_message(self, message, client=None):
        if client is None:
            client = self
        #print "<--", repr(message)
        if not hasattr(client, 'user_id'):
            return

        try:
            battle = self.current_client_battles[client.user_id]
        except KeyError:
            logging.debug('%r not in any battle' % client)
            return

        if message.get('answer'):
            self._check_answer(battle, self, message['answer'])
        elif message.get('alternatives'):
            self._get_alternatives(battle, self)

        elif message.get('timed_out'):
            self._timed_out(battle, self)

        elif message.get('next_question'):
            # this is going to be hit twice, within nanoseconds of each other.
            t = time.time()
            #if not hasattr(battle, 'min_wait_delay'):
            #    # something is very wrong!
            #    print "current_question", getattr(battle, 'current_question', '*no current question*')
            #    print repr(battle)

            if battle.min_wait_delay > t:
                logging.debug('%r min_wait_delay=%r, t=%r'%(self, battle.min_wait_delay,t))
                client.send(dict(error={'message': 'Too soon',
                                        'code': errors.ERROR_NEXT_QUESTION_TOO_SOON}))
                return
            if battle.stopped:
                #client.send({'error': 'Battle already stopped'})
                return
            if not battle.current_question:
                question = self._get_next_question(battle)
                if question:
                    image = None
                    if question.has_image():
                        image = question.get_image().render_attributes

                    battle.current_question = question
                    if battle.has_computer_participant():
                        qk = (self.db.QuestionKnowledge.collection
                              .one({'question.$id': question._id}))
                        battle.send_question(battle.current_question,
                                             knowledge=qk,
                                             image=image)
                    else:
                        battle.send_question(battle.current_question,
                                             image=image)
                    if not image:
                        battle.set_now()
                    battle.save_played_question(self.db)
                else:
                    battle.send_to_all(
                      dict(error={'message': "No more questions! Run out!",
                                  'code': errors.ERROR_NO_MORE_QUESTIONS})
                    )
                    battle.save_play(self.db, halted=True)
                    battle.stop()
        elif message.get('against_computer'):
            battle = None
            for created_battle in self.battles:
                if created_battle.is_open():
                    if self in created_battle.participants:
                        battle = created_battle
            if battle:
                bot = self.db.User.one({'username': settings.COMPUTER_USERNAME})
                if not bot:
                    bot = self.db.User()
                    bot.username = settings.COMPUTER_USERNAME
                    bot.save()
                assert bot
                battle.add_participant(ComputerClient(str(bot._id), bot.username))
                self.current_client_battles[client.user_id] = battle
                if battle.ready_to_play():
                    battle.commence(self.db)

            else:
                client.send(dict(error={'message': "You're not waiting in an open battle",
                                      'code': errors.ERROR_NOT_IN_OPEN_BATTLE}))

        elif message.get('bot_answers'):
            if not battle.current_question:
                return

            outcome = battle.bot_answer
            # note that we can't use 'self' because what we want to do is
            # reenact these events for the bot
            bot = battle.get_computer_participant()
            if outcome['right']:
                if outcome['alternatives']:
                    #self.on_message({'alternatives': 1}, client=bot)
                    self._get_alternatives(battle, bot)
                self._check_answer(battle, bot, battle.current_question.answer)
            elif outcome['wrong']:
                if outcome['alternatives']:
                    self._get_alternatives(battle, bot)
                self._check_answer(battle, bot, '**deliberately wrong**')

        elif message.get('still_alive'):
            battle.still_alive()

        elif message.get('loaded_image'):
            if not battle.is_stopped():
                self._loaded_image(battle, self)

        else: # pragma: no cover
            print message
            raise NotImplementedError("Unrecognized message %r" % message)

    def _loaded_image(self, battle, client):
        battle.remember_loaded_image(client)
        if battle.has_all_loaded_image():
            battle.set_now()
            battle.send_to_all(dict(show_image=1))

    def _timed_out(self, battle, client):
        if not battle.current_question:
            # happens if the timed_out is sent even though someone has
            # already answered correctly
            #print "current_question", getattr(battle, 'current_question', '*no current question*')
            #print repr(battle)
            #print getattr(battle, 'min_wait_delay', '*no min_wait_delay*')
            #print repr(client)
            assert battle.is_waiting() or battle.is_stopped()
            return
        if battle.timed_out_too_soon():
            logging.debug("time.time():%s current_question_sent+thinking_time:%s"
                            % (time.time(),
                               battle.current_question_sent +
                               battle.rules['thinking_time']))
            client.send(dict(error={'message': 'Timed out too soon',
                                    'code': errors.ERROR_TIMED_OUT_TOO_SOON}))
            return

        battle.remember_timed_out(client)
        battle.save_played_question(self.db, client, timed_out=True)
        if battle.has_everyone_answered_or_timed_out():
            for participant in battle.participants:
                if not battle.has_answered(participant):
                    participant.send({'answered': {'too_slow': True}})
            battle.close_current_question()
            if battle.has_more_questions():
                battle.send_wait(3, dict(next_question=True))
            else:
                battle.conclude()
                battle.save_play(self.db, finished=True,
                                 winner=battle.get_winner())

    def _check_answer(self, battle, client, answer):
        if not battle.current_question:
            # form submitted too late
            return
        if battle.has_answered(client):
            #client.send({'error': 'You have already answered this question'})
            client.send(dict(error={'message':'You have already answered this question',
                                    'code': errors.ERROR_ANSWERED_TWICE}))
            return
        if battle.has_image() and not battle.has_all_loaded_image():
            client.send(dict(error={
              'message':'Not all participants have loaded the question',
              'code': errors.ERROR_ANSWER_BEFORE_IMAGE_LOADED
            }))
            battle.stop()
            return
        battle.remember_answered(client)
        time_ = battle.get_time()
        if battle.check_answer(answer):
            # client got it right!!
            points = 3
            if battle.has_loaded_alternatives(client):
                points = 1
            client.send({'answered': {'right': True}})
            for participant in battle.participants:
                if participant is client:
                    continue
                if battle.has_answered(participant):
                    participant.send({'answered': {'beaten': True}})
                else:
                    participant.send({'answered': {'too_slow': True}})
            battle.increment_score(client, points)
            battle.save_played_question(self.db, client,
                                        answer=answer,
                                        time_=time_,
                                        right=True)
            battle.close_current_question()
            if battle.has_more_questions():
                battle.send_wait(3, dict(next_question=True))
            else:
                battle.conclude()
                winner = battle.get_winner()
                if winner is None:
                    winner = False
                battle.save_play(self.db, finished=True,
                                 winner=winner)

        else:
            # you suck!
            client.send({'answered': {'right': False}})
            battle.send_to_everyone_else(client,
              {'has_answered': client.user_name}
            )
            battle.save_played_question(self.db, client,
                                        answer=answer,
                                        time_=time_,
                                        right=False)

            if battle.has_everyone_answered():
                battle.close_current_question()
                battle.send_to_all({'answered':{'both_wrong': True}})
                if battle.has_more_questions():
                    battle.send_wait(3, dict(next_question=True))
                else:
                    battle.conclude()
                    battle.save_play(self.db, finished=True,
                                     winner=battle.get_winner())


    def _get_alternatives(self, battle, client):
        if not battle.current_question:
            assert battle.is_waiting() or battle.is_stopped()
            return
        assert battle.current_question
        if not battle.has_loaded_alternatives(client):
            battle.send_alternatives(client)
            battle.save_played_question(self.db, client, alternatives=True)

    def _get_next_question(self, battle):
        def has_question_knowledge(question):
            try:
                qk = (self.db.QuestionKnowledge.collection
                  .one({'question.$id': question._id}))
            except MultipleResultsFound:
                logging.warning("For question id %s there are multiple question_knowledge" %
                                 question._id)
                for each in (self.db.QuestionKnowledge.collection
                  .one({'question.$id': question._id})):
                    qk = each
                    break
            if qk:
                return qk['users']
            return False

        # don't bother checking if the bot has played them recently
        battle_user_ids = [x.user_id for x in battle.participants
                           if not x.is_bot]

        battle_user_object_ids = [ObjectId(x) for x in battle_user_ids]
        then = datetime.datetime.now() - datetime.timedelta(seconds=60 * 60)
        recently_played = (self.db.Play.collection
                           .find({'users.$id': {'$in': battle_user_object_ids},
                                  'finished': {'$gte': then}
                                  }))
        recently_played_ids = [x['_id'] for x in recently_played]
        recently_played_questions = (self.db.PlayedQuestion.collection
                                    .find({'play.$id': {'$in': recently_played_ids}}))
        recently_played_questions_ids = set([x['question'].id for x in recently_played_questions])

        sent_questions = [x._id for x in battle.sent_questions]
        search = {'state': 'PUBLISHED',
                  '_id':{'$nin': sent_questions + list(recently_played_questions_ids)}}
        if battle.rules['genres']:
            search['genre.$id'] = {'$in': [x for x in battle.rules['genres']]}

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
                if question.author and str(question.author._id) in battle_user_ids:
                    search['_id']['$nin'].append(question._id)
                elif question.has_image() and not question.get_image().render_attributes:
                    logging.warn("render_attributes missing for %r" % question.get_image()._id)
                    search['_id']['$nin'].append(question._id)
                elif battle.has_computer_participant() and not has_question_knowledge(question):
                    search['_id']['$nin'].append(question._id)
                elif battle.rules['pictures_only'] and not question.has_image():
                    search['_id']['$nin'].append(question._id)
#                elif not question.has_image():
#                    search['_id']['$nin'].append(question._id)
                else:
                    return question

    def on_close(self):
        if getattr(self, 'user_id', None) and getattr(self, 'user_name', None):
            try:
                battle = self.current_client_battles[self.user_id]
            except KeyError:
                logging.debug('%r not in any battle' % self.user_id)
                return

            try:
                battle.remove_participant(self)
            except KeyError:
                # for some bizarre reason this client has already disconnected
                return
            battle.send_to_all({'disconnected': self.user_name})
            battle.stop()

            # did it ever even start?
            if battle.play_id:
                if battle.get_play(self.db):
                    battle.save_play(self.db, halted=True)
                else:
                    # XXX I have no idea how this could happen!
                    # but it appears to happen sometimes when one user is stuck
                    logging.warning("There is a play_id %r but not Play" % battle.play_id)

class BattlesDebugHandler(tornado.web.RequestHandler):
    def get(self):
        out = ['BATTLES:']
        for i, battle in enumerate(self.application.battles):
            line = []
            line.append(('%s.' % (i + 1)).ljust(3))
            line.append(str(id(battle)).ljust(15))
            line.append((', '.join(repr(x.user_name) for x in battle.participants)).ljust(50))
            if battle.is_dead(10):
                line.append('DEAD')
            elif battle.is_stopped():
                line.append('STOPPED')
            elif battle.is_open():
                line.append('OPEN')
            else:
                line.append('IN ACTION!')
            out.append(''.join(line))
        self.set_header("Content-Type", "text/plain")
        self.write('\n'.join(out))

class Application(tornado.web.Application):
    battles = set()
    current_client_battles = {}

    def __init__(self, database_name, **kwargs):
        handlers = [tornadio.get_router(Client).route()]
        handlers.append((r"/battles", BattlesDebugHandler))
        tornado.web.Application.__init__(self, handlers, **kwargs)
        self.database_name = database_name
        self.con = connection

    @property
    def db(self):
        return self.con[self.database_name]


from tornado.options import options
application = Application(
      database_name=options.database_name,
      debug=options.debug,
      enabled_protocols=['websocket',
                         'flashsocket',
                         #'xhr-multipart',
                         #'xhr-polling'
                         ],
      flash_policy_port=options.flashpolicy and 843 or None,
      flash_policy_file=(options.flashpolicy and
                        op.abspath(options.flashpolicy) or None),
      socket_io_port=options.port,
    )
