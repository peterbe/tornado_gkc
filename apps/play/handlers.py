import re
import datetime
from string import zfill
from random import randint
from collections import defaultdict
from pymongo import ASCENDING, DESCENDING
from pymongo.objectid import InvalidId, ObjectId
import tornado.web
from tornado.web import HTTPError
from apps.main.handlers import BaseHandler
from apps.play.models import PlayPoints
from utils.routes import route
from utils import dict_plus
import settings


class BasePlayHandler(BaseHandler):

    def find_play(self, play_id):
        if isinstance(play_id, basestring):
            try:
                play_id = ObjectId(play_id)
            except InvalidId:
                return None
        return self.db.Play.one({'_id': play_id})

    def must_find_play(self, play_id, user):
        play = self.find_play(play_id)
        if not play:
            raise HTTPError(404, "Play can't be found")
        if user not in play.users:
            if not self.is_admin_user(user):
                raise HTTPError(403, "Not your play")
        return play


@route('/play/start/$', name='start_play')
class StartPlayingHandler(BasePlayHandler):

    def get_next_anonymous_username(self):
        #count = self.db.User.find({'anonymous': True}).count()
        def random_username():
            return u'anonymous%s' % zfill(randint(1, 1000), 4)
        username = random_username()
        while self.db.User.collection.one({'username': username}):
            username = random_username()
        return username

    def is_username_taken(self, username):
        return (self.db.User
              .find({'username': re.compile(re.escape(username), re.I),
                     'anonymous': False})
              .count())

    def get(self):
        if not self.get_current_user():
            # create a anoynmous temporary user and
            user = None
            username = self.get_argument('username', '').strip()
            if username:
                if self.is_username_taken(username):
                    raise HTTPError(400, "Username already taken")
                else:
                    user = (self.db.User
                            .one({'username': re.compile(re.escape(username), re.I),
                                  'anonymous': True}))
            else:
                username = self.get_next_anonymous_username()
            if not user:
                user = self.db.User()
                user.username = username
                user.anonymous = True
                user.save()
            self.set_secure_cookie("user", str(user._id), expires_days=1)

        self.redirect(self.reverse_url('play'))

@route('/play/start/check_username.json$', name='start_play_check_username')
class StartPlayingHandler(StartPlayingHandler):
    def get(self):
        data = {}
        username = self.get_argument('username', '').strip()
        if not username:
            data['username'] = self.get_next_anonymous_username()
        elif self.is_username_taken(username):
            data['taken'] = True
        else:
            data['username'] = username

        self.write_json(data)


@route('/play/start/(\w{24})$', name='start_play_rule')
class StartPlayingByRulesHandler(StartPlayingHandler):

    def get(self, _id):
        try:
            rules = self.db.Rules.one({'_id': ObjectId(_id)})
        except InvalidId:
            raise HTTPError(404, "ID invalid")
        if not rules:
            raise HTTPError(404, "Rules unknown")

        self.set_secure_cookie('rules', str(rules._id))
        super(StartPlayingByRulesHandler, self).get()



@route('/play/battle$', name='play')
class PlayHandler(BasePlayHandler):

    @tornado.web.authenticated
    def get(self):
        options = self.get_base_options()
        user = self.get_current_user()
        user_settings = self.get_user_settings(user)
        config = {
          'SOCKET_PORT': 8888,
          'HIGHSCORE_URL': '/play/highscore/',
          'HOMEPAGE_URL': '/',
          'DEBUG': self.application.settings['debug'],
          'ENABLE_SOUNDS': not getattr(user_settings, 'disable_sound', False),
        }
        options['user_settings'] = user_settings
        options['config_json'] = tornado.escape.json_encode(config)
        self.render("play/play.html", **options)


@route('/play/replay/(\w{24})/$', name='replay_play')
class ReplayPlayHandler(BasePlayHandler):

    @tornado.web.authenticated
    def get(self, play_id):
        options = self.get_base_options()
        play = self.must_find_play(play_id, options['user'])
        play = self.find_play(play_id)
        options['play'] = play
        player_names_lookup = {}
        for user in play.users:
            player_names_lookup[user._id] = unicode(user)
        player_names = player_names_lookup.values()

        def sort_me_first(x, y):
            if x == unicode(options['user']):
                return -1
            else:
                return 1
        player_names.sort(sort_me_first)
        options['player_names'] = player_names
        played_questions = (self.db.PlayedQuestion.collection
          .find({'play.$id': play._id}).sort('add_date', ASCENDING))

        questions = []
        outcomes = defaultdict(dict)
        totals = defaultdict(int)
        series = defaultdict(list)  # to use for the graph
        for played_question in played_questions:
            if played_question['question'].id not in questions:
                questions.append(played_question['question'].id)
            player_name = player_names_lookup[played_question['user'].id]
            outcomes[played_question['question'].id][player_name] = \
              dict_plus(played_question)
            if played_question['right']:
                if played_question['alternatives']:
                    totals[player_name] += 1
                else:
                    totals[player_name] += 3
            series[player_name].append(
              totals[player_name]
            )
        # now turn this series dict into a list
        series = [dict(name=k, data=[0] + v) for (k, v) in series.items()]
        options['series_json'] = tornado.escape.json_encode(series)

        questions = [dict_plus(self.db.Question.collection.one({'_id':x}))
                      for x in questions]
        genres = {}
        images = {}
        for q in questions:
            if q._id in genres:
                name = genres[q._id]
            else:
                genres[q._id] = u'xxx'
            q.genre = dict_plus(dict(name=genres[q._id]))
        for question_image in (self.db.QuestionImage
          .find({'question.$id': {'$in': [x._id for x in questions]}})):
            images[question_image.question._id] = question_image
        options['images'] = images
        options['questions'] = questions
        options['outcomes'] = outcomes
        options['totals'] = totals
        options['page_title'] = ' vs. '.join(player_names)
        options['message_sent'] = None
        options['can_send_message'] = not options['user'].anonymous
        if settings.COMPUTER_USERNAME in player_names:
            options['can_send_message'] = False

        options['play_messages'] = (self.db.PlayMessage
                               .find({'play.$id': play._id})
                               .sort('add_date'))

        self.render("play/replay.html", **options)


@route('/play/replay/$', name='play_replays')
@route('/play/replay/(all)/$', name='all_play_replays')
class ReplaysHandler(BasePlayHandler):

    @tornado.web.authenticated
    def get(self, all=None):
        options = self.get_base_options()
        search_base = {'users.$id': options['user']._id}
        stats = dict(wins=0,
                     draws=0,
                     losses=0)
        long_ago = datetime.datetime(2011, 1, 1, 0, 0, 0)
        for play in (self.db.Play
          .find(dict(search_base, finished={'$gte': long_ago}))):
            if play.winner == options['user']:
                stats['wins'] += 1
            elif play.draw:
                stats['draws'] += 1
            else:
                stats['losses'] += 1

        options['stats'] = stats
        options['plays'] = (self.db.Play.find(search_base)
                             .sort('add_date', DESCENDING))
        options['page_title'] = "Past plays"

        self.render("play/replays.html", **options)


@route('/play/(\w{24})/send-message/$', name='send_play_message')
class SendPlayMessageHandler(BasePlayHandler):

    @tornado.web.authenticated
    def post(self, play_id):
        options = self.get_base_options()
        play = self.must_find_play(play_id, options['user'])
        message = self.get_argument('message').strip()
        if not message:
            raise HTTPError(400, "message can't be empty")
        elif len(message) > 100:
            raise HTTPError(400, "message too long")
        to = self.get_argument('to', None)
        if to:
            try:
                to_user = self.db.User.one({'_id': ObjectId(to)})
            except InvalidId:
                raise HTTPError(400, "Invalid to user")
        else:
            to_user = play.get_other_user(options['user'])

        play_message = self.db.PlayMessage()
        play_message.play = play
        play_message.message = message
        play_message['from'] = options['user']
        play_message.to = to_user
        play_message.save()

        self.push_flash_message(
            "Message from %s" % options['user'].username,
            message,
            user=to_user,
            #url=self.reverse_url('play_message', play_message._id),
            )

        url = self.reverse_url('replay_play', play._id)
        url += '#message_sent'
        self.redirect(url)


@route('/play/highscore/$', name='play_highscore')
class PlayHighscoreHandler(BaseHandler):

    def get(self, rules=None):
        options = self.get_base_options()
        search = {'points': {'$gt': 0}}
        computer = (self.db.User.collection
          .one({'username': settings.COMPUTER_USERNAME}))
        if computer:
            search['user.$id'] = {'$ne': computer['_id']}
        if rules:
            search['rules'] = rules._id
        play_points = (self.db.PlayPoints
                       .find(search)
                       .sort('points', -1)
                       )
        options['play_points'] = play_points
        options['page_title'] = "Highscore"
        options['rules'] = rules
        self.render("play/highscore.html", **options)


@route('/play/highscore/(\w{24})$', name='play_highscore_rules')
class PlayHighscoreRulesHandler(PlayHighscoreHandler):

    def get(self, _id):
        try:
            rules = self.db.Rules.one({'_id': ObjectId(_id)})
        except InvalidId:
            raise HTTPError(404, "ID invalid")
        if not rules:
            raise HTTPError(404, "Rules unknown")
        super(PlayHighscoreRulesHandler, self).get(rules=rules)


@route('/play/update_points.json$', name='play_update_points_json')
class UpdatePointsJSONHandler(BasePlayHandler):

    def get(self):
        user = self.get_current_user()
        if not user:
            raise HTTPError(403, "Forbidden")
        play_id = self.get_argument('play_id')
        play = self.must_find_play(play_id, user)
        play_points_before = self.get_play_points(user, rules_id=play.rules._id)
        points_before = getattr(play_points_before, 'points', 0)
        highscore_position_before = getattr(play_points_before,
                                            'highscore_position', None)
        play_points = PlayPoints.calculate(user, play.rules._id)
        play_points.update_highscore_position()
#        if user.anonymous:
#            login_url = self.reverse_url('login')
#            self.write_json(dict(anonymous=True,
#                                 login_url=login_url,
#                                 points=play_points.points))
#            return

        increment = play_points.points - points_before
        result = dict(
          increment=increment,
          points_before=points_before,
          points=play_points.points,
          highscore_position_before=highscore_position_before,
          highscore_position=play_points.highscore_position,
        )
        if user.anonymous:
            result['login_url'] = self.reverse_url('login')
        if not play.rules.default:
            result['highscore_url'] = self.reverse_url('play_highscore_rules',
                                                       play.rules._id)
        else:
            result['highscore_url'] = self.reverse_url('play_highscore')

#        from pprint import pprint
#        print "USER", user['username']
#        pprint(result)
        self.write_json(result)


@route('/play/render_image_attributes/', name="render_image_attributes")
class RenderImageAttributesHandler(BaseHandler):

    def get(self):
        search = {'render_attributes': None}
        search = {}
        limit = int(self.get_argument('limit', 99))

        _module = self.application.ui_modules['ShowQuestionImageThumbnail']
        module = _module(self)
        outs = []
        for question_image in (self.db.QuestionImage.collection
                                .find(search)
                                .limit(limit)):
            if not (self.db.Question.collection
                    .one({'_id': question_image['question'].id})):
                (self.db.QuestionImage.collection
                 .remove({'_id': question_image['_id']}))
                continue
            question_image = (self.db.QuestionImage
                              .one({'_id': question_image['_id']}))
            outs.append((repr(question_image.question.text),
                         module.render(question_image, (300, 300),
                                alt=question_image.question.text,
                                save_render_attributes=True,
                                return_json=True)))

        self.set_header("Content-Type", "text/plain")
        if outs:
            self.write('\n\n'.join('\n'.join(x) for x in outs))
        else:
            self.write('nothing\n')
