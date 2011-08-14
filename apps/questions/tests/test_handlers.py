import os
import base64
import json
import re
from time import mktime
import datetime
from apps.main.tests.base import BaseHTTPTestCase, TestClient
from utils import format_time_ampm, get_question_slug_url
import utils.send_mail as mail
from utils.http_test_client import TestClient
from apps.questions.models import *

import settings

class LoginError(Exception):
    pass


class HandlersTestCase(BaseHTTPTestCase):

    def setUp(self):
        super(HandlersTestCase, self).setUp()
        if '__test' not in settings.THUMBNAIL_DIRECTORY:
            settings.THUMBNAIL_DIRECTORY += '__test'

    def tearDown(self):
        super(HandlersTestCase, self).setUp()
        assert '__test' in settings.THUMBNAIL_DIRECTORY
        self._rm_thumbnails(settings.THUMBNAIL_DIRECTORY)

    def _rm_thumbnails(self, dir, rmdir=False):
        for each in os.listdir(dir):
            path = os.path.join(dir, each)
            if os.path.isdir(path):
                self._rm_thumbnails(path, rmdir=True)
            elif os.path.isfile(path):
                os.remove(path)
        if rmdir and not os.listdir(dir):
            os.rmdir(dir)

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
                    alternatives=" Bra  \nOk\nFine\nIlla",
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

    def test_adding_question_with_same_accept(self):
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
                    accept="brA",
                    alternatives=" Bra  \nOk\nFine\nIlla",
                    genre="Life ",
                    spell_correct='yes',
                    comment="  \nSome\nComment\t"
                    )
        response = self.client.post(url, data)
        self.assertEqual(response.code, 302)
        redirected_to = response.headers['Location']
        assert self.db.Question.find().count()
        question, = self.db.Question.find()
        self.assertEqual(question.answer, u'Bra')
        self.assertEqual(question.alternatives,
                         [u'Bra', u'Ok', u'Fine', u'Illa'])
        self.assertEqual(question.accept, [])

    def test_edit_question_with_same_accept(self):
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
        data = dict(answer="Wilde",
                    text="Who was gay?",
                    accept='wilde',
                    alternatives=['Oscar','Wilde','Shake','Spere'],
                    comment="\tchanged\n",
                    genre='lit',
                    )
        response = self.client.post(url, data)
        #self.assertEqual(response.code, 200)
        #self.assertTrue('errors' in response.body)
        #data['alternatives'] = ['wilde','Dickens','Shake','Spere']
        response = self.client.post(url, data)
        self.assertEqual(response.code, 302)

        question = self.db.Question.one({'answer':u"Wilde"})
        self.assertEqual(question.accept, [])


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
        maths = self.db.Genre()
        maths.name = u"Maths"
        maths.approved = True
        maths.save()

        q1 = self.db.Question()
        q1.text = u"One?"
        q1.answer = u"1"
        q1.author = bob
        q1.submit_date = datetime.datetime.now()
        q1.accept_date = datetime.datetime.now()
        q1.state = ACCEPTED
        q1.genre = maths
        q1.save()

        q2 = self.db.Question()
        q2.text = u"Two?"
        q2.answer = u"2"
        q2.author = bob
        q2.submit_date = datetime.datetime.now()
        q2.accept_date = datetime.datetime.now()
        q2.state = ACCEPTED
        q2.genre = maths
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
        q3.genre = maths
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
        self._login()
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
        assert not maths.approved

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
        submitted_url = self.reverse_url('submitted_question', question._id)
        self.assertEqual(submitted_url, response.headers['location'])
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
        self.assertEqual(response.code, 302)
        self.assertEqual(response.headers['Location'], self.reverse_url('questions'))
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

        maths = self.db.Genre.one(dict(name=maths.name))
        self.assertTrue(not maths.approved)

        maths = self.db.Genre.one(dict(name=maths.name))
        self.assertTrue(not maths.approved)

        geography = self.db.Genre.one({'name':'Geography'})
        self.assertTrue(geography.approved)

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

    def test_published_questions(self):
        self._login()
        url = self.reverse_url('questions_published')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)

        maths = self.db.Genre()
        maths.name = u'Maths'
        maths.approved = True
        maths.save()

        celebs = self.db.Genre()
        celebs.name = u'Celebs'
        celebs.approved = True
        celebs.save()

        user = self.db.User.one()
        assert user

        now = datetime.datetime.now()

        q1 = self.db.Question()
        q1.author = user
        q1.text = u'Question 1?'
        q1.answer = u'yes'
        q1.genre = maths
        q1.publish_date = now
        q1.state = PUBLISHED
        q1.save()

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('Question 1?' in response.body)
        self.assertTrue('Maths' in response.body)

        question_image = self.db.QuestionImage()
        question_image.question = q1
        question_image.save()
        here = os.path.dirname(__file__)
        image_data = open(os.path.join(here, 'image.png'), 'rb').read()
        with question_image.fs.new_file('original') as f:
            type_, __ = mimetypes.guess_type('image.png')
            f.content_type = type_
            f.write(image_data)
        self.assertTrue(q1.has_image())
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('/thumbnails' in response.body)

    def test_adding_question_with_image(self):
        self._login()
        user = self.db.User.one(username='peterbe')
        assert user

        maths = self.db.Genre()
        maths.name = u'Celebs'
        maths.approved = True
        maths.save()

        url = self.reverse_url('add_question')
        data = dict(text=u"H\ex3r mar dU? ",
                    answer="Bra   ",
                    accept="Hyffsat",
                    alternatives=" Bra  \nOk\nFine\nIlla",
                    genre="Life ",
                    spell_correct='yes',
                    comment=""
                    )
        # simulate clicking on the right submit button
        data['add_image'] = 1
        response = self.client.post(url, data)
        self.assertEqual(response.code, 302)
        question, = self.db.Question.find()
        assert question.answer == u'Bra'
        new_image_url = self.reverse_url('new_question_image', question._id)
        self.assertEqual(response.headers['Location'], new_image_url)

        response = self.client.get(new_image_url)
        self.assertTrue('type="file"' in response.body)
        edit_url = self.reverse_url('edit_question', question._id)
        self.assertTrue(edit_url in response.body)

        here = os.path.dirname(__file__)
        image_data = open(os.path.join(here, 'image.png'), 'rb').read()
        assert image_data
        content_type, data = encode_multipart_formdata([('image', 'image.png')],
                                         [('image', 'image.png', image_data)])
        response = self.client.post(new_image_url, data,
                                    headers={'Content-Type': content_type})
        self.assertEqual(response.code, 302)
        question, = self.db.Question.find()
        submit_url = self.reverse_url('submit_question', question._id)
        self.assertEqual(response.headers['location'], submit_url)
        # don't submit yet but check that there's a thumbnail on the submit
        # confirmation page
        response = self.client.get(submit_url)
        img_tag = self._find_thumbnail_tag(response.body)
        self.assertTrue(img_tag)
        self.assertEqual(img_tag['alt'], question.text)
        response = self.client.get(img_tag['src'])
        from PIL import Image
        from cStringIO import StringIO
        img = Image.open(StringIO(response.body))
        self.assertEqual(img.size, (75,18)) # known from fixture
        self.assertEqual(img_tag['width'], '75')
        self.assertEqual(img_tag['height'], '18')

        # go back and change image
        edit_url = self.reverse_url('edit_question', question._id)
        response = self.client.get(edit_url)
        img_tag = self._find_thumbnail_tag(response.body)
        self.assertTrue(img_tag)

        response = self.client.get(new_image_url)
        self.assertEqual(response.code, 200)

        img_tag = self._find_thumbnail_tag(response.body)
        self.assertTrue(img_tag)
        self.assertEqual(img_tag['alt'], question.text)

        image_data = open(os.path.join(here, 'screenshot.jpg'), 'rb').read()
        content_type, data = encode_multipart_formdata([('image', 'image.jpg')],
                                         [('image', 'image.jpg', image_data)])
        response = self.client.post(new_image_url, data,
                                    headers={'Content-Type': content_type})
        self.assertEqual(response.code, 302)
        self.assertEqual(response.headers['location'], submit_url)

        response = self.client.get(submit_url)
        img_tag = self._find_thumbnail_tag(response.body)
        self.assertTrue(img_tag)
        self.assertEqual(img_tag['alt'], question.text)
        response = self.client.get(img_tag['src'])
        from PIL import Image
        from cStringIO import StringIO
        img = Image.open(StringIO(response.body))
        self.assertEqual(img.size, (300, 236)) # known from fixture
        self.assertEqual(img_tag['width'], '300')
        self.assertEqual(img_tag['height'], '236')

        # now submit it
        response = self.client.post(submit_url, {})
        self.assertEqual(response.code, 302)
        submitted_url = self.reverse_url('submitted_question', question._id)
        self.assertEqual(submitted_url, response.headers['location'])
        # view that
        response = self.client.get(submitted_url)
        self.assertEqual(response.code, 200)

        question, = self.db.Question.find()
        self.assertEqual(question.state, 'SUBMITTED')

        admin = TestClient(self)
        self._login('admin',
                    email=settings.ADMIN_EMAILS[0],
                    client=admin)

        response = admin.get(self.reverse_url('questions'))
        self.assertTrue('Submitted Questions (1)' in response.body)
        img_tag = self._find_thumbnail_tag(response.body)
        self.assertTrue(img_tag)

        response = self.client.get(img_tag['src'])
        img = Image.open(StringIO(response.body))
        self.assertEqual(img.size, (20, 16)) # known from fixture
        self.assertEqual(img_tag['width'], '20')
        self.assertEqual(img_tag['height'], '16')

        response = admin.get(self.reverse_url('view_question', question._id))
        img_tag = self._find_thumbnail_tag(response.body)
        self.assertTrue(img_tag)
        self.assertEqual(img_tag['alt'], question.text)
        response = self.client.get(img_tag['src'])
        img = Image.open(StringIO(response.body))
        self.assertEqual(img.size, (300, 236)) # known from fixture
        self.assertEqual(img_tag['width'], '300')
        self.assertEqual(img_tag['height'], '236')

        accept_url = self.reverse_url('accept_question', question._id)
        response = admin.post(accept_url, {})
        self.assertEqual(response.code, 302)
        question, = self.db.Question.find()
        self.assertEqual(question.state, 'ACCEPTED')

        bob = TestClient(self)
        self._login('bob',
                    email='bob@test.com',
                    client=bob)
        random_review_url = self.reverse_url('review_random')
        response = bob.get(random_review_url)
        img_tag = self._find_thumbnail_tag(response.body)
        self.assertTrue(img_tag)
        self.assertEqual(img_tag['alt'], question.text)
        response = self.client.get(img_tag['src'])
        img = Image.open(StringIO(response.body))
        self.assertEqual(img.size, (300, 236)) # known from fixture
        self.assertEqual(img_tag['width'], '300')
        self.assertEqual(img_tag['height'], '236')

        publish_url = self.reverse_url('publish_question', question._id)
        response = admin.post(publish_url, {})
        self.assertEqual(response.code, 302)
        question, = self.db.Question.find()
        self.assertEqual(question.state, 'PUBLISHED')

        published_url = self.reverse_url('questions_published')
        response = self.client.get(published_url)
        img_tag = self._find_thumbnail_tag(response.body)
        self.assertTrue(img_tag)

        response = self.client.get(img_tag['src'])
        img = Image.open(StringIO(response.body))
        self.assertEqual(img.size, (20, 16)) # known from fixture
        self.assertEqual(img_tag['width'], '20')
        self.assertEqual(img_tag['height'], '16')


    def test_editing_question_with_image(self):
        self._login()
        user = self.db.User.one(username='peterbe')
        assert user

        maths = self.db.Genre()
        maths.name = u'Celebs'
        maths.approved = True
        maths.save()

        question = self.db.Question()
        question.author = user
        question.text = u'How?'
        question.answer = u'yes'
        question.alternatives = [u'yes', u'no', u'maybe', u'ok']
        question.genre = maths
        question.save()

        here = os.path.dirname(__file__)
        image_data = open(os.path.join(here, 'image.png'), 'rb').read()
        question_image = self.db.QuestionImage()
        question_image.question = question
        question_image.save()

        type_, __ = mimetypes.guess_type('image.png')
        with question_image.fs.new_file('original') as f:
            f.content_type = type_
            f.write(image_data)

        question_image, = self.db.QuestionImage.find()
        assert not question_image.render_attributes

        edit_question_url = self.reverse_url('edit_question', question._id)
        response = self.client.get(edit_question_url)
        first_src = self._find_thumbnail_tag(response.body)['src']
        first_height = self._find_thumbnail_tag(response.body)['height']
        assert first_height == '18'  # know your fixtures :)
        new_image_url = self.reverse_url('new_question_image', question._id)
        self.assertTrue(new_image_url in response.body)

        question_image, = self.db.QuestionImage.find()
        first_render_attributes = question_image.render_attributes
        assert first_render_attributes

        response = self.client.get(new_image_url)
        assert self._find_thumbnail_tag(response.body)['height'] == '18'

        # prepare to upload a different one

        image_data = open(os.path.join(here, 'screenshot.jpg'), 'rb').read()
        content_type, data = encode_multipart_formdata([('image', 'image.jpg')],
                                         [('image', 'image.jpg', image_data)])
        response = self.client.post(new_image_url, data,
                                    headers={'Content-Type': content_type})
        self.assertEqual(response.code, 302)
        submit_url = self.reverse_url('submit_question', question._id)
        self.assertEqual(response.headers['location'], submit_url)

        response = self.client.get(edit_question_url)
        second_src = self._find_thumbnail_tag(response.body)['src']
        second_height = self._find_thumbnail_tag(response.body)['height']

        self.assertNotEqual(first_src, second_src)
        self.assertNotEqual(first_height, second_height)

        question_image, = self.db.QuestionImage.find()
        second_render_attributes = question_image.render_attributes
        self.assertNotEqual(first_render_attributes, second_render_attributes)

    def test_viewing_public_question(self):
        user = self.db.User()
        user.username = u'peterbe'
        user.save()

        maths = self.db.Genre()
        maths.name = u'Celebs'
        maths.approved = True
        maths.save()

        question = self.db.Question()
        question.author = user
        question.text = u"How many (number) 'apple' are there?"
        question.answer = u'yes'
        question.alternatives = [u'yes', u'no', u'maybe', u'ok']
        question.genre = maths
        question.publish_date = (datetime.datetime.now() -
                                 datetime.timedelta(days=1))
        question.save()

        url = get_question_slug_url(question)
        response = self.client.get(url)
        self.assertEqual(response.code, 404)  # not published

        question.publish_date = (datetime.datetime.now() -
                                 datetime.timedelta(days=1))
        question.state = PUBLISHED
        question.save()

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue(question.text in response.body)

    def _find_thumbnail_tag(self, content):
        return list(self._find_thumbnail_tags(content))[0]

    def _find_thumbnail_tags(self, content):
        for each in re.findall('<img\s*[^>]+>', content):
            attrs = dict(re.findall('(\w+)="([^"]+)"', each))
            if 'thumbnails' in attrs['src']:
                yield attrs



import mimetypes
def encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\r\n'
    L = []
    for (key, value) in fields:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)
    for (key, filename, value) in files:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
        L.append('Content-Type: %s' % get_content_type(filename))
        L.append('')
        L.append(value)
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body

def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'
