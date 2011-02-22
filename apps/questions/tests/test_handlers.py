import base64
import re
from time import mktime
import datetime
from apps.main.tests.base import BaseHTTPTestCase, TestClient
from utils import format_time_ampm
import utils.send_mail as mail

class LoginError(Exception):
    pass


class HandlersTestCase(BaseHTTPTestCase):
    def _login(self):
        user = self.get_db().Users.one(username='peterbe')
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
        user = self.get_db().User.one(username='peterbe')
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
        user = self.get_db().User.one(username='peterbe')
        assert user

        url = self.reverse_url('add_question')
        response = self.get(url, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)

        assert not self.get_db().Question.find().count()
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
        assert self.get_db().Question.find().count()
        assert self.get_db().Genre.find().count()
        question = self.get_db().Question.one()
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
