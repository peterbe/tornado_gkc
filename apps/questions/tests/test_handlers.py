import base64
import json
import re
from time import mktime
import datetime
from apps.main.tests.base import BaseHTTPTestCase, TestClient
from utils import format_time_ampm
import utils.send_mail as mail
from utils.http_test_client import TestClient
from apps.questions.models import *

import settings

class LoginError(Exception):
    pass


class HandlersTestCase(BaseHTTPTestCase):

    def test_questions_shortcut(self):
        cookie = self._login() # using fixtures

        url = self.reverse_url('questions_shortcut')
        response = self.client.get(url)
        self.assertEqual(response.code, 301)
        redirected_to = response.headers['Location']
        url = self.reverse_url('questions')
        self.assertTrue(redirected_to.endswith(url))



    def test_adding_question(self):
        url = self.reverse_url('add_question')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)

        self._login()
        user = self.db.User.one(username='peterbe')
        assert user

        url = self.reverse_url('add_question')
        response = self.client.get(url)
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
        response = self.client.post(url, data)
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
        response = self.client.get(junk_edit_url)
        self.assertEqual(response.code, 404)

        junk_edit_url = self.reverse_url('edit_question',
          str(question._id).replace('0','1'))
        response = self.client.get(junk_edit_url)
        self.assertEqual(response.code, 404)

        edit_url = self.reverse_url('edit_question', question._id)
        response = self.client.get(edit_url)
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
        response = self.client.post(edit_url, data)
        self.assertEqual(response.code, 200)
        self.assertTrue('errors' in response.body)
        data = dict(data, text="A new question?")
        response = self.client.post(edit_url, data)
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
        response = self.client.get(url)
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
        response = self.client.post(url, data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertTrue('errors' in response.body)
        data['alternatives'] = ['wilde','Dickens','Shake','Spere']
        response = self.client.post(url, data)

        self.assertEqual(response.code, 302)
        question = self.db.Question.one({'answer':u"Wilde"})
        self.assertEqual(question.text, data['text'])
        self.assertEqual(question.answer, data['answer'])
        self.assertTrue('Wilde' in question.alternatives)
        self.assertEqual(question.genre.name, u"Lit")
        self.assertEqual(question.comment, data['comment'].strip())

        submit_url = self.reverse_url('submit_question', question._id)
        response = self.client.get(url)
        self.assertTrue(submit_url in response.body)

        response = self.client.get(submit_url)
        self.assertEqual(response.code, 200)
        response = self.client.post(submit_url, {})
        self.assertEqual(response.code, 302)
        question = self.db.Question.one({'answer':u"Wilde"})
        self.assertTrue(question.submit_date)
        self.assertEqual(question.state, SUBMITTED)

        view_url = self.reverse_url('view_question', question._id)

        # now that it's submitted you can't edit it
        response = self.client.get(url)
        self.assertEqual(response.code, 403)
        response = self.client.post(url, data)
        self.assertEqual(response.code, 403)
        # same thing happens if you try to submit it again
        response = self.client.get(submit_url)
        self.assertEqual(response.code, 403)

        response = self.client.post(submit_url, {})
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
        response = self.client.get(url)

        # dislike the first one
        data = dict(verdict=WRONG,
                    comment="Not right",
                    rating="Bad")
        response = self.client.post(review_urls[0], data)
        self.assertEqual(response.code, 302)
        self.assertTrue(url in response.headers['Location'])
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue(review_urls[1] in response.body)
        # dislike the first one
        data = dict(verdict=VERIFIED,
                    rating="OK")
        response = self.client.post(review_urls[1], data)
        self.assertEqual(response.code, 302)
        response = self.client.get(url)
        self.assertTrue('No questions to review' in response.body)

    def test_editing_someone_elses_question(self):

        url = self.reverse_url('add_question')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)

        self._login()
        user = self.db.User.one(username='peterbe')
        assert user

        url = self.reverse_url('add_question')
        response = self.client.get(url)
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
        response = self.client.post(url, data)
        self.assertEqual(response.code, 302)
        redirected_to = response.headers['Location']
        assert self.db.Question.find().count()

        question = self.db.Question.one()
        ashley = self.db.User()
        ashley.username = u'ashley'
        ashley.save()
        question.author = ashley
        question.save()

        url = self.reverse_url('edit_question', question._id)
        response = self.client.get(url)
        self.assertEqual(response.code, 403)

        response = self.client.post(url, data)
        self.assertEqual(response.code, 403)

    def test_genre_names_json(self):
        url = self.reverse_url('genre_names_json')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue(not struct['names'])

        ashley = self.db.User()
        ashley.username = u'ashley'
        ashley.save()

        geography = self.db.Genre()
        geography.name = u'Geo'
        geography.save()

        question = self.db.Question()
        question.text = u"??"
        question.answer = u"!"
        question.author = ashley
        question.genre = geography
        question.save()

        maths = self.db.Genre()
        maths.name = u'Maths'
        maths.save()

        question = self.db.Question()
        question.text = u"??2"
        question.answer = u"!2"
        question.author = ashley
        question.genre = maths
        question.save()

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['names'], ['Geo', 'Maths'])

    def test_question_lifecycle(self):
        url = self.reverse_url('questions')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue('/login/' in response.headers['Location'])

        user = self._login()
        assert user

        # add a draft question
        add_url = self.reverse_url('add_question')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue(add_url in response.body)

        maths = self.db.Genre()
        maths.name = u'Maths'
        maths.save()

        question = self.db.Question()
        question.text = u'Who likes milk?'
        question.answer = u'cats'
        question.author = user
        question.state = DRAFT
        question.genre = maths
        question.save()

        question.add_date -= datetime.timedelta(minutes=1)
        edit_question_url = self.reverse_url('edit_question', question._id)
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue(edit_question_url in response.body)
        self.assertTrue('draft questions (1)' in response.body.lower())

        response = self.client.get(edit_question_url)
        self.assertEqual(response.code, 200)
        submit_question_url = self.reverse_url('submit_question', question._id)
        #assert not question.can_submit()
        response = self.client.post(submit_question_url, {})
        self.assertEqual(response.code, 400)

        self.assertTrue(submit_question_url not in response.body)
        question.alternatives = [u'1', u'2', u'3', u'4']
        question.save()
        #assert question.can_submit()
        response = self.client.get(edit_question_url)
        self.assertTrue(submit_question_url in response.body)

        response = self.client.get(submit_question_url)
        self.assertEqual(response.code, 200)

        admin = TestClient(self)
        self._login('admin',
                    email=settings.ADMIN_EMAILS[0],
                    client=admin)

        response = admin.get(submit_question_url)
        self.assertEqual(response.code, 200)

        dude = TestClient(self)
        self._login('greg', client=dude)

        response = dude.get(submit_question_url)
        self.assertEqual(response.code, 403)
        response = dude.post(submit_question_url, {})
        self.assertEqual(response.code, 403)

        response = self.client.post(submit_question_url, {})
        self.assertEqual(response.code, 302)
        self.assertEqual(url, response.headers['location'])
        response = self.client.get(url)
        self.assertEqual(response.code, 200)

        self.assertTrue('submitted questions (1)' in response.body.lower())
        self.assertTrue(edit_question_url not in response.body)
        view_question_url = self.reverse_url('view_question', question._id)
        self.assertTrue(view_question_url in response.body)

        # if you view it, observe that you're not allowed to review it
        response = self.client.get(view_question_url)
        self.assertEqual(response.code, 200)
        self.assertTrue(question.text in response.body)
        self.assertTrue('Submitted:' in response.body)

        response = dude.get(view_question_url)
        self.assertEqual(response.code, 403) # not accepted yet

        response = admin.get(view_question_url)
        self.assertEqual(response.code, 200)
        self.assertTrue('Admin actions' in response.body)

        # reject it first
        reject_question_url = self.reverse_url('reject_question', question._id)
        data = {'reject_comment': 'Too long'}
        response = self.client.post(reject_question_url, data)
        self.assertEqual(response.code, 403) # not an admin
        response = dude.post(reject_question_url, data)
        self.assertEqual(response.code, 403) # not an admin
        response = admin.post(reject_question_url, data)
        self.assertEqual(response.code, 302)
        question = self.db.Question.one({'_id':question._id})
        assert question.state == REJECTED

        response = self.client.get(url)
        self.assertTrue('rejected questions (1)' in response.body.lower())

        response = self.client.get(edit_question_url)
        self.assertEqual(response.code, 200)
        response = admin.get(edit_question_url)
        self.assertEqual(response.code, 200)

        data = dict(answer=question.answer,
                    text="Short?",
                    accept='',
                    alternatives=[question.answer,'Dickens','Shake','Spere'],
                    comment="\tchanged\n",
                    genre="Geography",
                    )
        response = self.client.post(edit_question_url, data)
        self.assertEqual(response.code, 302)
        question = self.db.Question.one({'_id':question._id})
        assert question.text == "Short?"
        assert self.db.Genre.one({'name':'Geography'})

        # admin is allowed to do this too
        response = admin.post(edit_question_url, data)
        self.assertEqual(response.code, 302)

        question = self.db.Question.one({'_id':question._id})
        assert question.state == DRAFT

        # this time, use the "Save and submit" instead
        data['submit_question'] = 'yes'
        response = self.client.post(edit_question_url, data)
        self.assertEqual(response.code, 302)
        question = self.db.Question.one({'_id':question._id})
        assert question.state == SUBMITTED
        # as admin, accept it now
        accept_question_url = self.reverse_url('accept_question', question._id)
        response = admin.post(accept_question_url, {})
        question = self.db.Question.one({'_id':question._id})
        assert question.state == ACCEPTED

        response = self.client.get(url)
        self.assertTrue('submitted questions (0)' in response.body.lower())

        # this other dude should be able to review the question
        response = dude.get(url)
        review_random_url = self.reverse_url('review_random')
        self.assertTrue(review_random_url in response.body)

        response = dude.get(review_random_url)
        self.assertEqual(response.code, 200)
        review_question_url = self.reverse_url('review_question', question._id)

        data = {'rating':'Good',
                'difficulty': '-1',
                'comment': 'No comment',
                'verdict': 'VERIFIED',
                }
        response = self.client.post(review_question_url, data)
        self.assertEqual(response.code, 400) # can't review your own
        response = dude.post(review_question_url, data)
        self.assertEqual(response.code, 302)

        review = self.db.QuestionReview.one({'question.$id':question._id})
        assert review
        self.assertEqual(review.comment, data['comment'])
        self.assertEqual(review.rating, 1)
        self.assertEqual(review.difficulty, int(data['difficulty']))
        self.assertEqual(review.verdict, data['verdict'])
        assert review.user.username == 'greg'

        response = admin.get(view_question_url)
        publish_question_url = self.reverse_url('publish_question', question._id)
        self.assertEqual(response.code, 200)
        self.assertTrue(publish_question_url in response.body)

        response = self.client.post(publish_question_url, {})
        self.assertEqual(response.code, 403) # not admin

        response = admin.post(publish_question_url, {})
        self.assertEqual(response.code, 302)

        question = self.db.Question.one({'_id':question._id})
        assert question.state == PUBLISHED

    def test_adding_question_form_maxlengths(self):
        self._login()
        url = self.reverse_url('add_question')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        regex = re.compile('<input (.*?)name="text"(.*?)>', re.M)
        attrs = ' '.join(regex.findall(response.body)[0])
        self.assertTrue('maxlength=' in attrs)

        regex = re.compile('<input (.*?)name="answer"(.*?)>', re.M)
        attrs = ' '.join(regex.findall(response.body)[0])
        self.assertTrue('maxlength=' in attrs)

    def test_admin_editing_other_peoples_questions(self):
        self._login()
        peter = self.db.User.one()
        assert peter.email not in settings.ADMIN_EMAILS

        admin_client = TestClient(self)
        self._login('admin',
                    email=settings.ADMIN_EMAILS[0],
                    client=admin_client)

        geography = self.db.Genre()
        geography.name = u'Geo'
        geography.save()

        question = self.db.Question()
        question.text = u"??"
        question.answer = u"!"
        question.author = peter
        question.genre = geography
        question.state = DRAFT
        question.save()

        url = self.reverse_url('edit_question', question._id)

        response = admin_client.get(url)
        self.assertEqual(response.code, 200)

        response = self.client.get(url)
        self.assertEqual(response.code, 200)

        question.state = SUBMITTED
        question.submit_date = datetime.datetime.now()
        question.save()

        response = self.client.get(url)
        self.assertEqual(response.code, 403)

        response = admin_client.get(url)
        self.assertEqual(response.code, 200)

        question.state = ACCEPTED
        question.accept_date = datetime.datetime.now()
        question.save()

        response = self.client.get(url)
        self.assertEqual(response.code, 403)

        response = admin_client.get(url)
        self.assertEqual(response.code, 200)

        question.state = PUBLISHED
        question.accept_date = datetime.datetime.now()
        question.save()

        response = self.client.get(url)
        self.assertEqual(response.code, 403)

        response = admin_client.get(url)
        self.assertEqual(response.code, 200)
