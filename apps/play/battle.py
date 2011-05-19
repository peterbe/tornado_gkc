import time
from collections import defaultdict
from utils.edit_distance import EditDistance

class BattleError(Exception):
    pass
class Battle(object):

    def __init__(self, thinking_time,
                 min_no_people=2, max_no_people=2,
                 no_questions=10,
                 genres_only=None,
                 language=None):
        # how long time between the questions
        self.thinking_time = thinking_time
        self.min_no_people = min_no_people
        self.max_no_people = max_no_people
        self.no_questions = no_questions
        self.participants = set()
        #self.user_ids = set()
        #self.ready_to_play = False
        self.sent_questions = set()
        self.stopped = False
        self.scores = defaultdict(int)
        self.loaded_alternatives = set()
        self.attempted = set()
        self.timed_out = set()
        #self._checking_answer = set()
        #self._ready_to_play = False
        self.current_question = None
        self.current_question_sent = None
        self.genres_only = genres_only
        self.language = language

    def __repr__(self):
        vs = ' vs. '.join(['%s:%r' % (x.user_id, x.user_name) for x in self.participants])
        return '<Battle: %s>' % vs

    def add_participant(self, client):
        if not self.is_open():
            raise BattleError("can't add more participants. it's full")
        assert client.user_id and client.user_name
        self.participants.add(client)
        #if len(self.participants) >= self.min_no_people:
        #    self._ready_to_play = True

    def ready_to_play(self):
        return len(self.participants) >= self.min_no_people

    def remove_participant(self, client):
        self.participants.remove(client)
        if len(self.participants) < self.min_no_people:
            self.stopped = True

    def is_open(self):
        return (len(self.participants) < self.min_no_people
                and not self.stopped)

    def send_wait(self, seconds, next_message):
        self.min_wait_delay = time.time() + seconds
        self.send_to_all(dict(wait=seconds, message=next_message))

    def is_waiting(self):
        return self.min_wait_delay and self.min_wait_delay > time.time()

    def send_to_everyone_else(self, client, msg):
        for p in self.participants:
            if p != client:
                p.send(msg)

    def send_to_all(self, msg):
        #print repr(msg)
        for p in self.participants:
            #print "\t", time.time(), repr(p)
            p.send(msg)

    def has_more_questions(self):
        return len(self.sent_questions) < self.no_questions

    def send_question(self, question):
        self.sent_questions.add(question)
        self.current_question = question
        self.current_question_sent = time.time()
        #print "SENDING", repr(self.current_question.text)
        #print self.current_question_sent
        #print
        packaged_question = {
          'id': str(question._id),
          'text': question.text,
          'genre': question.genre.name,
        }
        self.send_to_all(dict(question=packaged_question,
                              thinking_time=self.thinking_time))

    def close_current_question(self):
        self.current_question = None
        self.current_question_sent = None
        self.clear_answered()
        self.clear_timed_out()
        self.clear_loaded_alternatives()

    ## Timed out

    def remember_timed_out(self, client):
        self.timed_out.add(client)

    def clear_timed_out(self):
        self.timed_out = set()

    def has_all_timed_out(self):
        return len(self.timed_out) == len(self.participants)

    def timed_out_too_soon(self):
        assert self.current_question_sent
        return time.time() < (self.current_question_sent + self.thinking_time)

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
        print self.scores

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

    ## Concluding

    def conclude(self):
        winner = self.get_winner()
        if not winner:
            self.send_to_all({'winner': {'draw': True}})
        else:
            winner.send({'winner': {'you_won': True}})
            self.send_to_everyone_else(winner, {'winner': {'you_won': False}})
        self.stop()
