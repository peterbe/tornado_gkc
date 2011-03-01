import base64
import re
from time import mktime
import datetime
from apps.main.tests.base import BaseHTTPTestCase, TestClient
from utils import format_time_ampm
import utils.send_mail as mail
from apps.questions.models import *
class LoginError(Exception):
    pass


class HandlersTestCase(BaseHTTPTestCase):
    def _login(self):
        user = self.db.Users.one(dict(username=u'peterbe'))
        if user:
            raise NotImplementedError
        else:
            data = dict(username="peterbe",
                        email="mail@peterbe.com",
                        password="secret",
                        first_name="Peter",
                        last_name="Bengtsson")
            response = self.post('/user/signup/', data, follow_redirects=False)
            user_cookie = self.decode_cookie_value('user', response.headers['Set-Cookie'])
            user_id = base64.b64decode(user_cookie.split('|')[0])
            cookie = 'user=%s;' % user_cookie
        user = self.db.User.one(dict(username=u'peterbe'))
        assert user
        return cookie

    def test_questions_shortcut(self):
        cookie = self._login() # using fixtures

        url = self.reverse_url('questions_shortcut')
        response = self.get(url, follow_redirects=False,
                            headers={'Cookie':cookie})
        self.assertEqual(response.code, 301)
        redirected_to = response.headers['Location']
        url = self.reverse_url('questions')
        self.assertTrue(redirected_to.endswith(url))


    def test_adding_question(self):
        # first sign up
        cookie = self._login()
        user = self.db.User.one(username='peterbe')
        assert user

        url = self.reverse_url('add_question')
        response = self.get(url, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)

        assert not self.db.Question.find().count()
        data = dict(text=u"H\ex3r mar dU? ",
                    answer="Bra   ",
                    accept="Hyffsat",
                    alternatives=" Bra\nOk\nFine\nIlla",
                    genre="Life ",
                    spell_correct='yes',
                    comment="  \nSome\nComment\t"
                    )
        response = self.post(url, data, follow_redirects=False,
                             headers={'Cookie':cookie})
        self.assertEqual(response.code, 302)
        redirected_to = response.headers['Location']
        assert self.db.Question.find().count()
        assert self.db.Genre.find().count()
        question = self.db.Question.one()
        assert question

        self.assertEqual(question.answer, u"Bra")
        self.assertEqual(question.text, data['text'].strip())
        self.assertEqual(question.alternatives,
                         [x.strip() for x in data['alternatives'].splitlines()])
        self.assertEqual(question.genre.name, "Life")
        self.assertEqual(question.accept, [u"Hyffsat"])
        self.assertEqual(question.spell_correct, True)

        junk_edit_url = self.reverse_url('edit_question', '_'*24)
        response = self.get(junk_edit_url, headers={'Cookie':cookie})
        self.assertEqual(response.code, 404)

        junk_edit_url = self.reverse_url('edit_question',
          str(question._id).replace('0','1'))
        response = self.get(junk_edit_url, headers={'Cookie':cookie})
        self.assertEqual(response.code, 404)

        edit_url = self.reverse_url('edit_question', str(question._id))
        response = self.get(edit_url, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertTrue('>Some\nComment</textarea>' in response.body)
        point = response.body.find('name="spell_correct"'); assert point > -1
        area = response.body[point - 60: point + 60]
        self.assertTrue('checked' in area)
        self.assertTrue('value="Life"' in response.body)
        for alt in question.alternatives:
            self.assertTrue('value="%s"' % alt in response.body)
        self.assertTrue('value="Hyffsat"' in response.body)
        self.assertTrue('value="%s"' % question.text in response.body)
        self.assertTrue('value="%s"' % question.answer in response.body)

        data = dict(data, text="\t\t")
        response = self.post(edit_url, data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertTrue('errors' in response.body)
        data = dict(data, text="A new question?")
        response = self.post(edit_url, data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 302)

    def test_edit_and_submit(self):
        cookie = self._login()
        user = self.db.User.one(username='peterbe')
        assert user

        question = self.db.Question()
        question.text = u"Who wrote what?"
        question.answer = u"Dickens"
        question.accept = [u"Charles Dickens"]
        question.alternatives = [u"Dickens", u"One", u"Two", u"Three"]
        question.spell_check = True
        question.comment = u"Some Comment"
        genre = self.db.Genre()
        genre.name = u"Lit"
        genre.save()
        question.genre = genre
        question.author = user
        question.state = DRAFT
        question.save()

        url = self.reverse_url('edit_question', question._id)
        response = self.get(url, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)

        self.assertTrue('value="%s"' % question.text in response.body)
        self.assertTrue('value="%s"' % question.answer in response.body)
        self.assertTrue('value="%s"' % question.accept[0] in response.body)
        self.assertTrue('>%s</textarea>' % question.comment in response.body)
        for each in question.alternatives:
            self.assertTrue('value="%s"' % each in response.body)

        data = dict(answer="Wilde",
                    text="Who was gay?",
                    accept='Oscar Wilde',
                    alternatives=['Oscar','Dickens','Shake','Spere'],
                    comment="\tchanged\n",
                    genre='lit',
                    )
        response = self.post(url, data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertTrue('errors' in response.body)
        data['alternatives'] = ['wilde','Dickens','Shake','Spere']
        response = self.post(url, data, headers={'Cookie':cookie})

        self.assertEqual(response.code, 302)
        question = self.db.Question.one({'answer':u"Wilde"})
        self.assertEqual(question.text, data['text'])
        self.assertEqual(question.answer, data['answer'])
        self.assertTrue('Wilde' in question.alternatives)
        self.assertEqual(question.genre.name, u"Lit")
        self.assertEqual(question.comment, data['comment'].strip())

        submit_url = self.reverse_url('submit_question', question._id)
        response = self.get(url, headers={'Cookie':cookie})
        self.assertTrue(submit_url in response.body)

        response = self.get(submit_url, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        response = self.post(submit_url, {}, headers={'Cookie':cookie})
        self.assertEqual(response.code, 302)
        question = self.db.Question.one({'answer':u"Wilde"})
        self.assertTrue(question.submit_date)
        self.assertEqual(question.state, SUBMITTED)

        view_url = self.reverse_url('view_question', question._id)

        # now that it's submitted you can't edit it
        response = self.get(url, headers={'Cookie':cookie})
        self.assertEqual(response.code, 302)
        self.assertTrue(view_url in response.headers['Location'])
        response = self.post(url, data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 302)
        self.assertTrue(view_url in response.headers['Location'])
        # same thing happens if you try to submit it again
        response = self.get(submit_url, headers={'Cookie':cookie})
        self.assertEqual(response.code, 302)
        self.assertTrue(view_url in response.headers['Location'])
        response = self.post(submit_url, {}, headers={'Cookie':cookie})
        self.assertEqual(response.code, 302)
        self.assertTrue(view_url in response.headers['Location'])

    def test_review_random_question(self):
        bob = self.db.User()
        bob.username = u"bob"
        bob.save()
        q1 = self.db.Question()
        q1.text = u"One?"
        q1.answer = u"1"
        q1.author = bob
        q1.submit_date = datetime.datetime.now()
        q1.accept_date = datetime.datetime.now()
        q1.state = ACCEPTED
        q1.save()

        q2 = self.db.Question()
        q2.text = u"Two?"
        q2.answer = u"2"
        q2.author = bob
        q2.submit_date = datetime.datetime.now()
        q2.accept_date = datetime.datetime.now()
        q2.state = ACCEPTED
        q2.save()

        cookie = self._login()
        user = self.db.User.one({'username':'peterbe'})
        q3 = self.db.Question()
        q3.text = u"Two?"
        q3.answer = u"2"
        q3.author = user
        q3.submit_date = datetime.datetime.now()
        q3.accept_date = datetime.datetime.now()
        q3.state = ACCEPTED
        q3.save()

        url = self.reverse_url('review_random')
        all_review_urls = [self.reverse_url('review_question', x._id) for x
                       in self.db.Question.find()]
        self.assertEqual(len(all_review_urls), 3)
        review_urls = [self.reverse_url('review_question', x._id) for x
                       in self.db.Question.find({'author.$id':{'$ne':user._id}})]
        self.assertEqual(len(review_urls), 2)
        response = self.get(url, headers={'Cookie':cookie})

        # dislike the first one
        data = dict(verdict=WRONG,
                    comment="Not right",
                    rating="Bad")
        response = self.post(review_urls[0], data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 302)
        self.assertTrue(url in response.headers['Location'])
        response = self.get(url, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        #print response.body
        self.assertTrue(review_urls[1] in response.body)
        # dislike the first one
        data = dict(verdict=VERIFIED,
                    rating="OK")
        response = self.post(review_urls[1], data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 302)
        response = self.get(url, headers={'Cookie':cookie})
        self.assertTrue('No questions to review' in response.body)
