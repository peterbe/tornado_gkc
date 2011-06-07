import datetime
from collections import defaultdict
from pymongo import ASCENDING, DESCENDING
from pymongo.objectid import InvalidId, ObjectId
import tornado.web
from tornado.web import HTTPError
from apps.main.handlers import BaseHandler
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
        options['play'] = play
        player_names = [unicode(x) for x in play.users]
        def sort_me_first(x, y):
            if x == unicode(options['user']):
                return -1
            else:
                return 1
        player_names.sort(sort_me_first)
        options['player_names'] = player_names
        played_questions = (self.db.PlayedQuestion
          .find({'play.$id': play._id}).sort('add_date', ASCENDING))
        questions = []
        outcomes = defaultdict(dict)
        totals = defaultdict(int)
        for played_question in played_questions:
            if played_question.question not in questions:
                questions.append(played_question.question)
            player_name = unicode(played_question.user)
            outcomes[played_question.question._id][player_name] = played_question
            if played_question.right:
                if played_question.alternatives:
                    totals[player_name] += 1
                else:
                    totals[player_name] += 3
        #questions = [x.question for x in played_questions]
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
                       .find()
                       .sort('points', -1)
                       )
        options['play_points'] = play_points
        self.render("play/highscore.html", **options)
