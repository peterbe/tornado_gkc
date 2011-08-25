import datetime
import collections
import logging
from pymongo.objectid import ObjectId
from tornado.web import HTTPError
from utils.decorators import login_redirect, authenticated_plus
from utils.routes import route
from utils.html2text import html2text
from utils.send_mail import send_multipart_email
from apps.questions.models import (
  DRAFT, SUBMITTED, REJECTED, ACCEPTED, PUBLISHED
)
from apps.questions.handlers import QuestionsBaseHandler
import settings
import premailer


def frequency_to_timedelta(freq):
    if freq  == 'daily':
        return datetime.timedelta(days=1)
    if freq == 'weekly':
        return datetime.timedelta(days=7)
    if freq == 'bi-weekly':
        return datetime.timedelta(days=14)
    if freq == 'monthly':
        return datetime.timedelta(days=30)
    if freq == 'quarterly':
        return datetime.timedelta(days=91)  # 365/4


class NewsletterBaseHandler(QuestionsBaseHandler):

    def _get_newsletter_settings(self, user):
        newsletter_settings = self.db.NewsletterSettings.one({'user': user._id})
        if not newsletter_settings:
            # hasn't been set up before
            newsletter_settings = self.db.NewsletterSettings()
            newsletter_settings.user = user._id
            newsletter_settings.save()
        return newsletter_settings

    def _get_since(self, user):
        newsletter_settings = self._get_newsletter_settings(user)
        if newsletter_settings.last_send:
            return newsletter_settings.last_send
        now = datetime.datetime.utcnow()
        frequency = newsletter_settings.frequency
        timedelta = frequency_to_timedelta(frequency)
       	return newsletter_settings.next_send - timedelta

    def _get_frequency(self, user):
        newsletter_settings = self._get_newsletter_settings(user)

    def _set_next_newsletter(self, user):
        newsletter_settings = self._get_newsletter_settings(user)
        frequency = newsletter_settings.frequency
        timedelta = frequency_to_timedelta(frequency)
        now = datetime.datetime.utcnow()
        newsletter_settings.next_send = now + timedelta
        newsletter_settings.save()

    def render_html(self, user):
        options = {
          'user': user,
          'page_title': 'Newsletter to %s' % user.username,
        }
        since = self._get_since(user)
        date_search = {'$gte': since, '$lte': datetime.datetime.utcnow()}
        options['since'] = since

        newsletter_settings = self._get_newsletter_settings(user)
        options['frequency'] = newsletter_settings.frequency

        base_search = {'author.$id': user._id}
        # 1. published questions
        options['published'] = (self.db.Question
                     .find(dict(base_search,
                                publish_date=date_search,
                                state=PUBLISHED))
                     .sort('publish_date'))
        options['published_count'] = options['published'].count()

        # Accepted questions
        options['accepted'] = (self.db.Question
                     .find(dict(base_search,
                                accept_date=date_search,
                                state=ACCEPTED))
                     .sort('accept_date'))
        options['accepted_count'] = options['accepted'].count()

        # reviews to your accepted questions
        all_accepted_ids = [x['_id'] for x in
                            (self.db.Question.collection
                             .find(dict(base_search, state=ACCEPTED)))]

        reviews_search = {'question.$id': {'$in': all_accepted_ids},
                          'add_date': date_search}
        options['reviews'] = (self.db.QuestionReview
                              .find(reviews_search)
                              .sort('question.$id')
                              )
        options['reviews_count'] = options['reviews'].count()

        all_published_ids = [x['_id'] for x in
                            (self.db.Question.collection
                             .find(dict(base_search, state=PUBLISHED)))]

        options['total_published_count'] = (self.db.Question.collection
                             .find(dict(base_search, state=PUBLISHED))
                             .count())
        _plays = set()
        _unique_users = set()
        for pq in (self.db.PlayedQuestion.collection
                    .find({'question.$id': {'$in': all_published_ids},
                           #'add_date': date_search
                           })):
            _unique_users.add(pq['user'].id)
            _plays.add(pq['play'].id)
        options['played_count'] = len(_plays)
        options['unique_players_count'] = len(_unique_users)

        if not (options['published_count'] +
                options['accepted_count'] +
                options['reviews_count'] +
                options['played_count']):
            # don't bother with the html if there are questions
            return None

        html = self.render_string('newsletter/render.html', **options)
        return self._post_process(html)

    def _post_process(self, html):
        # Run premailer
        base_url = '%s://%s' % (self.request.protocol, self.request.host)
        html = premailer.transform(html, base_url=base_url)
        return html


@route('/newsletter/(\w{24})/preview/',
       name='newsletter_preview')
class NewsletterPreviewWrapperHandler(NewsletterBaseHandler):

    def get(self, _id):
        options = self.get_base_options()
        options['inner_url'] = self.reverse_url(
          'newsletter_preview_inner',
          _id
        )
        self.render('newsletter/preview.html', **options)

@route('/newsletter/(\w{24})/preview/inner/',
       name='newsletter_preview_inner')
class NewsletterPreviewHandler(NewsletterBaseHandler):

    def get(self, _id):
        user = self.db.User.one({'_id': ObjectId(_id)})
        html = self.render_html(user)
        if html is None:
            self.write("Nothing! to feature in this newsletter")
        else:
            self.write(html)


@route('/newsletter/(\w{24})/send/', name='newsletter_send')
class NewsletterSendHandler(NewsletterBaseHandler):

    def get(self, _id):
        user = self.db.User.one({'_id': ObjectId(_id)})
        assert user.email, user.username
        html = self.render_html(user)
        baseurl = ''

        plain_text = html2text(html, baseurl=baseurl)
        if self.get_argument('verbose', False):
            print plain_text

        subject = ("Kwissle newsletter (%s)" %
                   datetime.date.today().strftime('%d %b %Y'))
        try:
            send_multipart_email(self.application.settings['email_backend'],
                                 plain_text, html,
                                 subject,
                                 [user.email],
                                 settings.NEWSLETTER_SENDER,
                                 bcc='mail@peterbe.com')

        finally:
            logging.error("Unable to send %s's newsletter" % user.username)
            self._set_next_newsletter(user)

        self.write(user.email + '\n')


@route('/newsletter/preview/')
class NewsletterPreviewAnyHandler(NewsletterBaseHandler):  # pragma: no cover

    @authenticated_plus(lambda u: u.email in settings.ADMIN_EMAILS)
    def get(self):
        options = self.get_base_options()
        _published_users = collections.defaultdict(int)
        for q in (self.db.Question.collection
                  .find()):
            _published_users[q['author'].id] += 1
        published_users = []
        for u in self.db.User.find({'_id': {'$in': _published_users.keys()}}):
            published_users.append((_published_users[u._id], u))

        options['published_users'] = published_users
        self.render('newsletter/preview_any.html', **options)
