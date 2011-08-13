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
