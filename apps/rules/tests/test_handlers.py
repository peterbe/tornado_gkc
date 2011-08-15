import re
import datetime
import json
from apps.main.tests.base import BaseHTTPTestCase, TestClient

class HandlersTestCase(BaseHTTPTestCase):

    def test_adding_rules(self):
        url = self.reverse_url('rules_add')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)

        self._login()
        user = self.db.User.one(username='peterbe')
        assert user

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        data = {'no_questions': 'x',
                'thinking_time': 'x',
                'min_no_people': 2,
                'max_no_people': '2',
                'notes': 'Bla bla',
                }
        response = self.client.post(url, data)
        self.assertEqual(response.code, 200)
        self.assertTrue('errors' in response.body)

        data['name'] = 'My cool rules'
        data['no_questions'] = 9
        data['thinking_time'] = 16

        response = self.client.post(url, data)
        self.assertEqual(response.code, 302)

        rules = self.db.Rules.one({'author': user._id})
        self.assertEqual(rules.no_questions, 9)
        self.assertEqual(rules.thinking_time, 16)
        self.assertEqual(rules.min_no_people, 2)
        self.assertEqual(rules.max_no_people, 2)
        self.assertEqual(rules.default, False)
        self.assertEqual(rules.pictures_only, False)
        self.assertEqual(rules.alternatives_only, False)
        self.assertEqual(rules.notes, unicode(data['notes'].strip()))

    def test_playable_questions_json(self):
        url = self.reverse_url('playable_questions_json')
        response = self.client.get(url)
        self.assertEqual(response.code, 403)

        self._login()
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct, {'questions': 0,
                                  'with_knowledge': 0})

        q1 = self._create_question()
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct, {'questions': 1,
                                  'with_knowledge': 0})

        q2 = self._create_question()
        q2.state = u'DRAFT'
        q2.save()
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['questions'], 1)

        q3 = self._create_question()
        response = self.client.get(url, {'genres': q3.genre._id})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['questions'], 1)

        response = self.client.get(url, {'genres': [q3.genre._id, q2.genre._id]})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['questions'], 1)

        response = self.client.get(url, {'pictures_only': 'true'})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['questions'], 0)

        self._attach_image(q2)
        response = self.client.get(url, {'pictures_only': 'true'})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['questions'], 0)

        self._attach_image(q1)
        response = self.client.get(url, {'pictures_only': 'true'})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['questions'], 1)

        self._attach_image(q1)
        response = self.client.get(url,
          {'pictures_only': 'true', 'genres': q3.genre._id})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['questions'], 0)

        self._attach_image(q1)
        response = self.client.get(url,
          {'pictures_only': 'true', 'genres': q1.genre._id})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['questions'], 1)

    def test_playable_questions_json_with_knowledge(self):
        url = self.reverse_url('playable_questions_json')
        self._login()
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['questions'], 0)

        q1 = self._create_question()
        q2 = self._create_question()

        qk = self.db.QuestionKnowledge()
        qk.question = q1
        qk.right = 0.5
        qk.wrong = 0.1
        qk.alternatives_right = 0.1
        qk.alternatives_wrong = 0.1
        qk.too_slow = 0.1
        qk.timed_out = 0.1
        qk.users = 10
        qk.save()

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['questions'], 2)
        self.assertEqual(struct['with_knowledge'], 1)

    def test_rules_page(self):
        bob = self.db.User()
        bob.username = u'bob'
        bob.save()
        rules = self.db.Rules()
        rules.name = u"NAME"
        rules.author = bob._id
        rules.no_questions = 11
        rules.thinking_time = 12
        rules.save()

        url = self.reverse_url('rules_page', rules._id)
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue(u"NAME" in response.body)
        self.assertTrue(u'11' in response.body)
        self.assertTrue(u'12 seconds' in response.body)
        self.assertTrue(u'seconds ago' in response.body)
        self.assertTrue(u'Categories: All published' in response.body)

        rules.min_no_people = 3
        rules.max_no_people = 4
        rules.alternatives_only = True
        rules.save()
        url = self.reverse_url('rules_page', rules._id)
        response = self.client.get(url)
        self.assertEqual(response.code, 200)

        self.assertTrue(u'Alternatives available all the time' in response.body)
        self.assertTrue(u'Min. number of players: 3' in response.body)
        self.assertTrue(u'Max. number of players: 4' in response.body)
        self.assertTrue(u'Playable questions: 0' in response.body)
        self.assertTrue(u'if playing against the computer: 0' in response.body)

        q1 = self._create_question()
        response = self.client.get(url)
        self.assertTrue(u'Playable questions: 1' in response.body)
        self.assertTrue(u'if playing against the computer: 0' in response.body)
        self._attach_knowledge(q1)
        response = self.client.get(url)
        self.assertTrue(u'Playable questions: 1' in response.body)
        self.assertTrue(u'if playing against the computer: 1' in response.body)

        rules.pictures_only = True
        rules.save()
        response = self.client.get(url)
        self.assertTrue(u'Playable questions: 0' in response.body)
        self.assertTrue(u'if playing against the computer: 0' in response.body)

        self._attach_image(q1)
        response = self.client.get(url)
        self.assertTrue(u'Playable questions: 1' in response.body)
        self.assertTrue(u'if playing against the computer: 1' in response.body)

        # when never played
        self.assertTrue('Not been played yet' in response.body)

        luke = self.db.User()
        luke.username = u'luke'
        luke.save()

        p = self.db.Play()
        p.users = [bob, luke]
        p.rules = rules._id
        p.no_players = 2
        p.no_questions = 1
        p.started = datetime.datetime.now()
        p.halted = datetime.datetime.now()
        p.save()

        response = self.client.get(url)
        self.assertTrue('Not been played yet' in response.body)

        p.halted = None
        p.finished = datetime.datetime.now()
        p.save()

        pq = self.db.PlayedQuestion()
        pq.play = p
        pq.question = q1
        pq.user = bob
        pq.right = True
        pq.answer = u'yes'
        pq.time = 4.3
        pq.save()

        pq = self.db.PlayedQuestion()
        pq.play = p
        pq.question = q1
        pq.user = luke
        pq.right = False
        pq.alternatives = True
        pq.answer = u'wrong'
        pq.time = 2.6
        pq.save()

        response = self.client.get(url)
        self.assertTrue('Not been played yet' not in response.body)
        html_regex = re.compile('<.*?>')
        body = html_regex.sub('', response.body)
        self.assertTrue('Played 1 time' in body)
        self.assertTrue('2 different players' in body)
