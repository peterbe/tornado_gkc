from time import time
from collections import defaultdict

class Battle(object):

    def __init__(self, min_no_people=2, max_no_people=2, no_questions=10,
                 genres_only=None):
        self.min_no_people = min_no_people
        self.max_no_people = max_no_people
        self.no_questions = no_questions
        self.participants = set()
        #self.user_ids = set()
        #self.ready_to_play = False
        self.sent_questions = set()
        self.stopped = False
        self.scores = defaultdict(int)
        self.loaded_alternatives = []
        self.attempted = {}
        #self._checking_answer = set()
        self._ready_to_play = False
        self.current_question = None
        self.genres_only = genres_only

    def add_participant(self, client):
        assert client.user_id and client.user_name
        self.participants.add(client)
        if len(self.participants) >= self.min_no_people:
            self._ready_to_play = True

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
        self.min_wait_delay = time() + seconds
        self.send_to_all(dict(wait=seconds, message=next_message))

    def send_to_everyone_else(self, client, msg):
        for p in self.participants:
            if p != client:
                p.send(msg)

    def send_to_all(self, msg):
        for p in self.participants:
            p.send(msg)

    #def send_next_question(self):
    #    raise NotImplementedError

    def send_question(self, question):
        self.sent_questions.add(question)
        self.current_question = question
        packaged_question = {
          'id': str(question._id),
          'text': question.text,
          'genre': question.genre.name,
        }
        self.send_to_all(dict(question=packaged_question))

    def increment_score(self, client, points):
        self.scores[client] += points

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
