from urlparse import urlparse
import mimetypes
import time
import os
import json
import datetime
from apps.main.tests.base import BaseHTTPTestCase, TestClient
from utils import get_question_slug_url


class HandlersTestCase(BaseHTTPTestCase):

    def _create_question(self,
                         text=None,
                         answer=u'yes',
                         alternatives=None,
                         accept=None,
                         spell_correct=False):
        cq = getattr(self, 'created_questions', 0)
        genre = self.db.Genre()
        genre.name = u"Genre %s" % (cq + 1)
        genre.approved = True
        genre.save()

        q = self.db.Question()
        q.text = text and unicode(text) or u'Question %s?' % (cq + 1)
        q.answer = unicode(answer)
        q.alternatives = (alternatives and alternatives
                          or [u'yes', u'no', u'maybe', u'perhaps'])
        q.genre = genre
        q.accept = accept and accept or []
        q.spell_correct = spell_correct
        q.state = u'PUBLISHED'
        q.publish_date = datetime.datetime.now()
        q.save()
        self.created_questions = cq + 1
        return q

    def _attach_image(self, question):
        question_image = self.db.QuestionImage()
        question_image.question = question
        question_image.render_attributes = {
          'src': '/static/image.jpg',
          'width': 300,
          'height': 260,
          'alt': question.text
        }
        question_image.save()

        here = os.path.dirname(__file__)
        image_data = open(os.path.join(here, 'image.jpg'), 'rb').read()
        with question_image.fs.new_file('original') as f:
            type_, __ = mimetypes.guess_type('image.jpg')
            f.content_type = type_
            f.write(image_data)

        assert question.has_image()

    def test_no_questions_point_json(self):
        url = self.reverse_url('stats_no_questions_point_json')
        self._login()
        q1 = self._create_question()
        assert q1.state == 'PUBLISHED', q1.state
        date = q1.publish_date + datetime.timedelta(days=2)
        assert date
        data = {
          'what': 'Questions',
          'timestamp': int(time.mktime(date.timetuple()))
        }
        response = self.client.get(url, data)
        self.assertEqual(response.code, 200)
        self.assertTrue(response.headers['content-type']
                        .startswith('application/json'))
        struct = json.loads(response.body)
        self.assertTrue(struct['items'])
        self.assertEqual(len(struct['items']), 1)
        item = struct['items'][0]
        self.assertEqual(item['text'], q1.text)
        self.assertEqual(item['url'],
                         get_question_slug_url(q1))
