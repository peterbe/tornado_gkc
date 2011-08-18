import datetime
from pprint import pprint
from pymongo.objectid import ObjectId
import time
from collections import defaultdict
from utils.edit_distance import EditDistance

from bot import ComputerClient, predict_bot_answer

class BattleError(Exception):
    pass

class Battle(object):

    def __init__(self, rules,
                 language=None):
        # how long time between the questions
        #self.thinking_time = thinking_time
        #self.min_no_people = min_no_people
        #self.max_no_people = max_no_people
        #self.no_questions = no_questions
        #self.genres = genres
        #self.pictures_only = pictures_only
        #self.alternatives_only = alternatives_only
        assert 'thinking_time' in rules
        assert 'no_questions' in rules
        assert 'min_no_people' in rules
        assert 'max_no_people' in rules
        assert 'genres' in rules
        assert 'pictures_only' in rules
        assert 'alternatives_only' in rules
        self.rules = rules

        self.participants = set()
        self.sent_questions = set()
        self.stopped = False
        self.scores = defaultdict(int)
        self.loaded_alternatives = set()
        self.attempted = set()
        self.timed_out = set()
        self.current_question = None
        self.loaded_image = set()
        self.current_question_sent = None
        self.language = language
        self.play_id = None
        self.updated = time.time()
        self.now = None

    def __repr__(self):
        vs = ' vs. '.join(['%s:%r' % (x.user_id, x.user_name) for x in self.participants])
        return '<Battle: %s>' % vs

    def add_participant(self, client, rules=None):
        if not self.is_open(rules=rules):
            raise BattleError("can't add more participants. it's full")
        assert client.user_id and client.user_name
        self.participants.add(client)

    def ready_to_play(self):
        return len(self.participants) >= self.rules['min_no_people']

    def remove_participant(self, client):
        self.participants.remove(client)
        if len(self.participants) < self.rules['min_no_people']:
            self.stopped = True

    def is_open(self, rules=None):
        if rules is not None:
            if rules['_id'] != self.rules['_id']:
                return False

        return (len(self.participants) < self.rules['min_no_people']
                and not self.stopped)

    def __contains__(self, client):
        return client.user_id in [x.user_id for x in self.participants]

    def send_wait(self, seconds, next_message):
        # the browser is told to wait for this many 'seconds' until it's allowed
        # to send the next "next_question=true" command.
        # Due to the inaccuracy of the timer in some browers, it might actually
        # fire slightly faster than this.
        # Therefore, allow for a tiny margin of error of being too quick.
        self.min_wait_delay = time.time() + seconds - 0.1
        self.send_to_all(dict(wait=seconds, message=next_message))

    def is_dead(self, age):
        assert age
        return time.time() > self.updated + age

    def still_alive(self):
        self.updated = time.time()

    def is_waiting(self):
        return self.min_wait_delay and self.min_wait_delay > time.time()

    def send_to_everyone_else(self, client, msg):
        for p in self.participants:
            if p != client:
                p.send(msg)

    def send_to_all(self, msg):
        for p in self.participants:
            p.send(msg)

    def has_more_questions(self):
        return len(self.sent_questions) < self.rules['no_questions']

    def send_question(self, question, knowledge=None, image=None):
        self.sent_questions.add(question)
        self.current_question = question
        self.current_question_sent = time.time()
        packaged_question = {
          'id': str(question._id),
          'text': question.text,
          'genre': question.genre.name,
        }
        if image is not None:
            packaged_question['image'] = image

        self.send_to_all(dict(question=packaged_question,
                              thinking_time=self.rules['thinking_time']))
        if knowledge:
            # depend on how easy the question is the bot will send
            # and answer in X seconds
            bot_answer = predict_bot_answer(self.rules['thinking_time'], knowledge)
            self.bot_answer = bot_answer
            self.send_to_all(dict(bot_answers=bot_answer['seconds']))
        else:
            self.bot_answer = None

    def close_current_question(self):
        self.current_question = None
        self.current_question_sent = None
        self.clear_answered()
        self.clear_timed_out()
        self.clear_loaded_alternatives()
        self.clear_loaded_image()

    def set_now(self):
        self.now = time.time()

    def get_time(self):
        return time.time() - self.now

    ## Convenient macros

    def has_computer_participant(self):
        return any([isinstance(p, ComputerClient) for p in self.participants])

    def get_computer_participant(self):
        return [p for p in self.participants
                if isinstance(p, ComputerClient)][0]

    def commence(self, db):
        self.send_to_all({
          'init_scoreboard': [x.user_name for x in self.participants],
          'thinking_time': self.rules['thinking_time'],
        })
        self.send_wait(3, dict(next_question=True))
        self.save_play(db, started=True)


    ## Timed out

    def remember_timed_out(self, client):
        self.timed_out.add(client)

    def clear_timed_out(self):
        self.timed_out = set()

    def has_all_timed_out(self):

        return len(self.timed_out) == len(self.participants)

    def timed_out_too_soon(self):
        assert self.current_question_sent
        return time.time() < (self.current_question_sent + self.rules['thinking_time'])

    def has_everyone_answered_or_timed_out(self):
        return (len(self.attempted) + len(self.timed_out)
          == len(self.participants))

    ## Answered

    def has_everyone_answered(self):
        return len(self.attempted) == len(self.participants)

    def has_answered(self, client):
        return client in self.attempted

    def remember_answered(self, client):
        self.attempted.add(client)

    def clear_answered(self):
        self.attempted = set()

    ## Alternatives

    def has_loaded_alternatives(self, client):
        return client in self.loaded_alternatives

    def remember_loaded_alternatives(self, client):
        self.loaded_alternatives.add(client)

    def clear_loaded_alternatives(self):
        self.loaded_alternatives = set()

    def send_alternatives(self, client):
        self.remember_loaded_alternatives(client)
        client.send(dict(alternatives=self.current_question.alternatives))

    ## Checking answer

    def check_answer(self, answer, _spell_correct=False):
        if self.stopped:
            return
        _answer = answer.lower().strip()
        if _spell_correct:
            ed = EditDistance([self.current_question.answer.lower()] +
                              [x.lower() for x in self.current_question.accept])
            if ed.match(_answer):
                return True

        if _answer == self.current_question.answer.lower():
            return True
        if self.current_question.accept:
            if _answer in [x.lower() for x in self.current_question.accept]:
                return True

        if not _spell_correct and self.current_question.spell_correct:
            return self.check_answer(answer, _spell_correct=True)

        return False

    ## Scoring

    def increment_score(self, client, points):
        self.scores[client] += points
        self.send_to_all({'update_scoreboard': [client.user_name, points]})

    def get_winner(self):
        best_points = -1
        winner = None
        tie = False
        for client, points in self.scores.items():
            if points > best_points:
                winner = client
                best_points = points
            elif points == best_points:
                tie = True
        if not tie:
            return winner

    def stop(self):
        self.stopped = True

    def is_stopped(self):
        return self.stopped

    ## Concluding

    def conclude(self):
        self.send_to_all({'play_id': str(self.play_id)})
        winner = self.get_winner()
        if not winner:
            self.send_to_all({'winner': {'draw': True}})
        else:
            winner.send({'winner': {'you_won': True}})
            self.send_to_everyone_else(winner,
                                       {'winner': {'you_won': False}})
        self.stop()

    ## Saving

    def save_play(self, db, started=False, halted=False, finished=False,
                  winner=None):
        assert started or halted or finished
        play = self.get_play(db)
        if started:
            play.started = datetime.datetime.now()
        elif halted:
            assert self.play_id
            play.halted = datetime.datetime.now()
        elif finished:
            assert self.play_id
            play.finished = datetime.datetime.now()
        if winner is not None:
            assert self.play_id
            if winner:
                user = db.User.one({'_id': ObjectId(winner.user_id)})
                assert user
                play.winner = user
            else:
                play.draw = True
        play.save()
        self.play_id = play._id

    def get_play(self, db):
        if self.play_id:
            play = db.Play.one({'_id': self.play_id})
        else:
            play = db.Play()
            play.rules = self.rules['_id']
            play.no_questions = self.rules['no_questions']
            play.no_players = 0
            for participant in self.participants:
                user = db.User.one({'_id': ObjectId(participant.user_id)})
                assert user
                play.users.append(user)
                play.no_players += 1
        return play

    def save_played_question(self, db, participant=None,
                             right=None,
                             answer=None,
                             alternatives=None,
                             timed_out=None,
                             time_=None):
        assert self.play_id
        play = self.get_play(db)
        if participant is None:
            # just setting up the played question
            for participant in self.participants:
                user = db.User.one({'_id': ObjectId(participant.user_id)})
                assert user
                played_question = db.PlayedQuestion()
                played_question.play = play
                played_question.user = user
                played_question.question = self.current_question
                played_question.save()
            return
        user = db.User.one({'_id': ObjectId(participant.user_id)})
        assert user
        played_question = db.PlayedQuestion.one({
          'play.$id': play._id,
          'user.$id': user._id,
          'question.$id': self.current_question._id,
        })
        if right is not None:
            assert answer is not None
            played_question.right = bool(right)
            played_question.answer = unicode(answer)
        elif alternatives is not None:
            played_question.alternatives = bool(alternatives)
        elif timed_out is not None:
            played_question.timed_out = bool(timed_out)
        else:
            raise Exception("Invalid parameters. Has to be something")
        if time_ is not None:
            played_question.time = time_
        played_question.save()

    ## Image
    ##

    def has_image(self):
        return self.current_question.has_image()

    def remember_loaded_image(self, client):
        self.loaded_image.add(client)

    def clear_loaded_image(self):
        self.loaded_image = set()

    def has_all_loaded_image(self):
        non_bot_participants = [x for x in self.participants
                                if not isinstance(x, ComputerClient)]
        return len(self.loaded_image) == len(non_bot_participants)
