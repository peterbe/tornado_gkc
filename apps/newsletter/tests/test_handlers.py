#import re
import datetime
from datetime import timedelta
#import json
from apps.main.tests.base import BaseHTTPTestCase
from apps.questions.models import (
  DRAFT, SUBMITTED, REJECTED, ACCEPTED, PUBLISHED,
  UNSURE
)
import settings

class HandlersTestCase(BaseHTTPTestCase):

    def test_previewing_newsletter(self):
        self._login()
        peter = self.db.User.one({'username': 'peterbe'})
        peter.email = unicode(settings.ADMIN_EMAILS[0])
        peter.save()

        chris = self.db.User()
        chris.username = u'chris'
        chris.email = u'chris@test.com'
        chris.save()

        url = self.reverse_url('newsletter_preview', chris._id)
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        iframe = self._get_html_attributes('iframe', response.body)[0]

        url = iframe['src']
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('Nothing' in response.body)

        newsletter_settings = self.db.NewsletterSettings.one({'user': chris._id})
        assert newsletter_settings
        # pretend that two weeks have gone
        days_into_future = (newsletter_settings.next_send -
                            datetime.datetime.utcnow()).days

        newsletter_settings.next_send = datetime.datetime.utcnow()
        newsletter_settings.last_send = (datetime.datetime.utcnow() -
                                         timedelta(days=days_into_future))
        newsletter_settings.save()

        maths = self.db.Genre()
        maths.name = u'Maths'
        maths.save()

        days = lambda x: timedelta(days=x)
        days_ago = lambda x: datetime.datetime.utcnow() - days(x)

        # Add a question
        q = self.db.Question()
        q.author = chris
        q.text = u'WAS THIS FUN?'
        q.answer = u'Yes'
        q.accept = []
        q.alternatives = [u'Yes', u'No', u'MAybe', u'Hmm']
        q.genre = maths
        q.state = SUBMITTED
        q.submit_date = days_ago(3)
        q.save()
        # ...still nothing
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('Nothing' in response.body)

        # Accept it
        q.state = ACCEPTED
        q.accept_date = datetime.datetime.utcnow()
        q.save()
        # ...it gets mentioned

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('accepted' in response.body.lower())
        self.assertTrue(q.text in response.body)

        # Post a review
        q.accept_date -= days(14)  # make it old
        q.save()

        r = self.db.QuestionReview()
        r.question = q
        r.user = peter
        r.verdict = UNSURE
        r.difficulty = 1  # Easy
        r.rating = -1  # 'Bad'
        r.comment = u"Are you really sure?"
        r.save()
        #r.add_date -= timedelta(seconds=1)
        #r.save()

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('unsure' in response.body.lower())
        self.assertTrue('Easy' in response.body)
        self.assertTrue('Bad' in response.body)
        self.assertTrue(q.text in response.body)

        # Publish it
        q.publish_date = datetime.datetime.utcnow()
        q.state = PUBLISHED
        q.save()
        # and pretend the review is really only
        r.add_date -= days(14)
        r.save()

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue(q.text in response.body)
        self.assertTrue('href="http' in response.body)

        # Play it
        outcome = [
          (3, 0),
          (0, 1)
        ]
        play = self._create_play([chris, peter], outcome=outcome,
                                 rules=None)
        assert play.finished
        for pq in self.db.PlayedQuestion.find({'play.$id': play._id}):
            if pq.question.text == 'Question 1?':
                pq.question = q
                pq.save()

        anon = self.db.User()
        anon.username = u'Anon'
        anon.anonymous = True
        anon.save()
        play2 = self._create_play([chris, peter], outcome=outcome,
                                 rules=None)
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('played' in response.body and
                        '1 time' in response.body)

        # Assign question knowledge
