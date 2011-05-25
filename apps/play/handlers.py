from collections import defaultdict
from pymongo import ASCENDING
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
        options = self.get_base_options()
        iframe_url = self.reverse_url('play')
        options['iframe_url'] = iframe_url
        #self.set_cookie('user_id', str(user._id))
        self.render("play/start_play.html", **options)

@route('/play/$', name='play')
class PlayHandler(BasePlayHandler):

    @tornado.web.authenticated
    def get(self):
        options = self.get_base_options()
        user = self.get_current_user()
        config = {
          'SOCKET_PORT': 8888,
          'HIGHSCORE_URL': '/play/highscore/',
          'HOMEPAGE_URL': '/',
          'DEBUG': self.application.settings['debug'],
        }
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
        self.render("play/replay.html", **options)
