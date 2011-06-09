import datetime
from collections import defaultdict
from pymongo import ASCENDING, DESCENDING
from pymongo.objectid import InvalidId, ObjectId
import tornado.web
from tornado.web import HTTPError
from apps.main.handlers import BaseHandler
from apps.play.models import PlayPoints
from utils.routes import route, route_redirect
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


route_redirect('/play/start$', '/play/start/', name='start_play_redirect')
@route('/play/start/$', name='start_play')
class StartPlayingHandler(BasePlayHandler):

    @tornado.web.authenticated
    def get(self):
        self.redirect(self.reverse_url('play'))


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
        for played_question in played_questions:
            if played_question['question'].id not in questions:
                questions.append(played_question['question'].id)
            player_name = player_names_lookup[played_question['user'].id]
            outcomes[played_question['question'].id][player_name] = dict_plus(played_question)
            if played_question['right']:
                if played_question['alternatives']:
                    totals[player_name] += 1
                else:
                    totals[player_name] += 3
        questions = [dict_plus(self.db.Question.collection.one({'_id':x}))
                      for x in questions]
        genres = {}
        for q in questions:
            if q._id in genres:
                name = genres[q._id]
            else:
                genres[q._id] = u'xxx'
            q.genre = dict_plus(dict(name=genres[q._id]))

        options['questions'] = questions
        options['outcomes'] = outcomes
        options['totals'] = totals
        options['page_title'] = ' vs. '.join(player_names)
        options['message_sent'] = None
        self.render("play/replay.html", **options)

@route('/play/replay/$', name='play_replays')
@route('/play/replay/(all)/$', name='all_play_replays')
class ReplaysHandler(BasePlayHandler):

    @tornado.web.authenticated
    def get(self, all=None):
        options = self.get_base_options()
        search_base = {'users.$id': options['user']._id}
        plays_base = (self.db.Play
                  .find(search_base)
                  )
        stats = dict(wins=0,
                     draws=0,
                     losses=0)
        long_ago = datetime.datetime(2011,1,1,0,0,0)
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

route_redirect('/play/highscore$', '/play/highscore/',
               name='play_highscore_shortcut')
@route('/play/highscore/$', name='play_highscore')
class PlayHighscoreHandler(BaseHandler):

    def get(self):
        options = self.get_base_options()
        play_points = (self.db.PlayPoints
                       .find({'points':{'$gt':0}})
                       .sort('points', -1)
                       )
        options['play_points'] = play_points
        options['page_title'] = "Highscore"
        self.render("play/highscore.html", **options)


@route('/play/update_points.json$', name='play_update_points_json')
class UpdatePointsJSONHandler(BasePlayHandler):

    def get(self):
        user = self.get_current_user()
        play_id = self.get_argument('play_id')
        play = self.must_find_play(play_id, user)
        play_points_before = self.get_play_points(user)
        points_before = getattr(play_points_before, 'points', 0)
        highscore_position_before = getattr(play_points_before,
                                            'highscore_position', None)
        play_points = PlayPoints.calculate(user)

        increment = play_points.points - points_before
        self.write_json(dict(increment=increment,
                             points_before=points_before,
                             points=play_points.points,
                             highscore_position_before=highscore_position_before,
                             highscore_position=play_points.highscore_position,
                             ))

class dict_plus(dict):
    def __init__(self, *args, **kwargs):
        if 'collection' in kwargs: # excess we don't need
            kwargs.pop('collection')
        dict.__init__(self, *args, **kwargs)
        self._wrap_internal_dicts()
    def _wrap_internal_dicts(self):
        for key, value in self.items():
            if isinstance(value, dict):
                self[key] = dict_plus(value)

    def __getattr__(self, key):
        return self[key]
