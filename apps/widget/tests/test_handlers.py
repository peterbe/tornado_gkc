from urlparse import urlparse
import json
from apps.main.tests.base import BaseHTTPTestCase


class HandlersTestCase(BaseHTTPTestCase):

    def test_random_question(self):
        q1 = self._create_question()
        q2 = self._create_question()

        self._attach_image(self._create_question())
        self._attach_image(self._create_question())

        url = self.reverse_url('widget_random_question_jsonp')
        response = self.client.get(url, {'callback': 'callback'})
        self.assertTrue(
          response.headers['Content-Type']
          .startswith('text/javascript'))
        self.assertTrue(response.body.startswith('callback('))
        self.assertTrue(response.body.endswith(')'))
        struct_str = response.body[len('callback('):-1]
        struct = json.loads(struct_str)
        self.assertTrue(struct['id'] in
          [str(x._id) for x in [q1, q2]])
        self.assertTrue(struct['text'] in
          [x.text for x in [q1, q2]])
        self.assertTrue(struct['alts'] in
          [x.alternatives for x in [q1, q2]])

    def test_preview(self):
        url = self.reverse_url('widget_preview')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)

    def test_answer(self):
        url = self.reverse_url('widget_answer')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertEqual(urlparse(response.headers['location']).path, '/')

        response = self.client.post(url, {})
        self.assertEqual(response.code, 400)
        response = self.client.post(url, {'id': '_'})
        self.assertEqual(response.code, 400)
        response = self.client.post(url, {'id': 'a' * 24})
        self.assertEqual(response.code, 404)

        q1 = self._create_question()
        q1.answer = u'RIGHTANSWER'
        q1.save()

        data = {'id': str(q1._id)}
        response = self.client.post(url, data)
        self.assertEqual(response.code, 200)
        self.assertTrue('No answer' in response.body)

        response = self.client.post(url, dict(data, answer='no'))
        self.assertEqual(response.code, 200)
        self.assertTrue('Sorry' in response.body)
        self.assertTrue(q1.answer in response.body)

        response = self.client.post(url, dict(data, answer='RightAnswer'))
        self.assertEqual(response.code, 200)
        self.assertTrue('Excellent' in response.body)

        assert not q1.spell_correct
        response = self.client.post(url, dict(data, answer='ightAnswer'))
        self.assertEqual(response.code, 200)
        self.assertTrue('Sorry' in response.body)
        self.assertTrue(q1.answer in response.body)

        q1.spell_correct = True
        q1.save()
        response = self.client.post(url, dict(data, answer='ightAnswer'))
        self.assertEqual(response.code, 200)
        self.assertTrue('Excellent' in response.body)

        response = self.client.post(url, dict(data, alt_answer='ightAnswer'))
        self.assertEqual(response.code, 200)
        self.assertTrue('Very good' in response.body)

    def test_answer_with_question_knowledge(self):
        url = self.reverse_url('widget_answer')
        q1 = self._create_question()

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

        data = {'id': str(q1._id)}
        response = self.client.post(url, dict(data, answer='Yes'))
        self.assertEqual(response.code, 200)

        response = self.client.post(url, dict(data, answer='No'))
        self.assertEqual(response.code, 200)

        response = self.client.post(url, dict(data, alt_answer='Yes'))
        self.assertEqual(response.code, 200)

        response = self.client.post(url, dict(data, alt_answer='No'))
        self.assertEqual(response.code, 200)

        qk.right = 0.2
        qk.wrong = 0.4
        qk.save()

        response = self.client.post(url, dict(data, answer='Yes'))
        self.assertTrue("You're smart" in response.body)
        self.assertEqual(response.code, 200)

        response = self.client.post(url, dict(data, answer='No'))
        self.assertEqual(response.code, 200)

        response = self.client.post(url, dict(data, alt_answer='Yes'))
        self.assertEqual(response.code, 200)

        response = self.client.post(url, dict(data, alt_answer='No'))
        self.assertEqual(response.code, 200)

        qk.right = 0.1
        qk.wrong = 0.5
        qk.save()

        response = self.client.post(url, dict(data, answer='Yes'))
        self.assertEqual(response.code, 200)
        self.assertTrue("You're really smart" in response.body)
