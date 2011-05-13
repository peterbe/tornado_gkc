import time
from collections import defaultdict

class Battle(object):

    def __init__(self, thinking_time,
                 min_no_people=2, max_no_people=2, no_questions=10,
                 genres_only=None):
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
        #self._checking_answer = set()
        #self._ready_to_play = False
        self.current_question = None
        self.current_question_sent = None
        self.genres_only = genres_only

    def add_participant(self, client):
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

    def send_to_everyone_else(self, client, msg):
        for p in self.participants:
            if p != client:
                p.send(msg)

    def send_to_all(self, msg):
        for p in self.participants:
            p.send(msg)

    def send_question(self, question):
        self.sent_questions.add(question)
        self.current_question = question
        self.current_question_sent = time.time()
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
        self.clear_loaded_alternatives()

    def timed_out_too_soon(self):
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

    def check_answer(self, answer, spell_correct=False):
        self.remember_answered(answer)
        _answer = answer.lower().strip()
        if spell_correct:
            raise NotImplementedError
        if _answer == self.current_question.answer.lower():
            return True
        if self.current_question.accept:
            if _answer in [x.lower() for x in self.current_question.accept]:
                return True

        if not spell_correct and self.current_question.spell_correct:
            return self.check_answer(answer, spell_correct=True)

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
            elif points == best_points:
                tie = True
        if not tie:
            return winner

    def stop(self):
        self.stopped = True
