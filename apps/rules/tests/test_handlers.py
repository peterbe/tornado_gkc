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
        self.assertEqual(struct, {'questions': 0})

        q1 = self._create_question()
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct, {'questions': 1})

        q2 = self._create_question()
        q2.state = u'DRAFT'
        q2.save()
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct, {'questions': 1})

        q3 = self._create_question()
        response = self.client.get(url, {'genres': q3.genre._id})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct, {'questions': 1})

        response = self.client.get(url, {'genres': [q3.genre._id, q2.genre._id]})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct, {'questions': 1})

        response = self.client.get(url, {'pictures_only': 'true'})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct, {'questions': 0})

        self._attach_image(q2)
        response = self.client.get(url, {'pictures_only': 'true'})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct, {'questions': 0})

        self._attach_image(q1)
        response = self.client.get(url, {'pictures_only': 'true'})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct, {'questions': 1})

        self._attach_image(q1)
        response = self.client.get(url,
          {'pictures_only': 'true', 'genres': q3.genre._id})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct, {'questions': 0})

        self._attach_image(q1)
        response = self.client.get(url,
          {'pictures_only': 'true', 'genres': q1.genre._id})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct, {'questions': 1})
