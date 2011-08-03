from time import mktime
from pprint import pprint
import datetime
from collections import defaultdict
from pymongo import ASCENDING, DESCENDING
from pymongo.objectid import InvalidId, ObjectId
import tornado.web
from tornado.web import HTTPError
from apps.main.handlers import BaseHandler
from utils.routes import route, route_redirect
from utils import parse_datetime, get_question_slug_url
import settings

route_redirect('/stats$', '/stats/')
@route('/stats/$', name='stats')
class StatsHandler(BaseHandler):
    def get(self):
        options = self.get_base_options()
        options['page_title'] = 'Statistics'
        self.render('stats/index.html', **options)

@route('/stats/login-method', name='stats_login_method')
class LoginMethodHandler(BaseHandler):
    def get(self):
        options = self.get_base_options()
        methods = defaultdict(int)
        total = 0
        for us in self.db.UserSettings.collection.find():
            if us['google']:
                methods['google'] += 1
            if us['twitter']:
                methods['twitter'] += 1
            if us['facebook']:
                methods['facebook'] += 1
            total += 1
        percentages = {}
        for t, n in methods.items():
            percentages[t] = int(100. * n / total)

        options['percentages'] = tornado.escape.json_encode(
          percentages
        )
        options['page_title'] = "Preferred login method"
        self.render('stats/login-method.html', **options)

class Getter(dict):
    def __getattr__(self, key):
        return self.get(key, None)#self.__getitem__(key)


@route('/stats/numbers', name='stats_numbers')
class NumbersHandler(BaseHandler):
    def get(self):
        options = self.get_base_options()
        facts = []

        facts.append(dict(label='Registered users',
                          number=self.db.User.find().count(),
                          url=self.reverse_url('stats_login_method')))

        facts.append(dict(label='Published questions',
                          number=self.db.Question
                            .find({'state':'PUBLISHED'}).count()))

        facts.append(dict(label='Questions pending review',
                          number=self.db.Question
                            .find({'state':'ACCEPTED'}).count(),
                          url=self.reverse_url('review_random')))

        facts.append(dict(label='Finished played games',
                          number=self.db.Play
                            .find({'finished':{'$ne':None}}).count()))

        facts.append(dict(label='Played questions',
                          number=self.db.PlayedQuestion
                            .find().count() / 2))

        facts.append(dict(label='Questions with images',
                          number=self.db.QuestionImage
                            .find().count() / 2))

        options['facts'] = [Getter(x) for x in facts]
        options['page_title'] = "Numbers"
        self.render('stats/numbers.html', **options)


@route('/stats/times', name='stats_times_played')
class TimesPlayedHandler(BaseHandler):

    def get(self):
        options = self.get_base_options()
        options['page_title'] = "Number of times registered users have played"
        played_times = defaultdict(int)
        for user in self.db.User.collection.find({'anonymous': False}):
            plays = (self.db.Play
              .find({'finished': {'$ne':None},
                     'users.$id': user['_id']})
              .count())
            if plays < 3:
                played_times[plays] += 1
            elif plays < 10:
                played_times['< 10'] += 1
            else:
                played_times['>= 10'] += 1

        total = sum(played_times.values())
        percentages = {}
        for key, count in played_times.items():
            percentages[key] = int(100.0 * count / total)
        options['percentages'] = percentages
        options['keys'] = sorted(played_times.keys())
        options['times'] = played_times
        self.render('stats/times.html', **options)


@route('/stats/battle-activity', name='stats_battle_activity')
class BattleActivityHandler(BaseHandler):

    def get(self):
        options = self.get_base_options()
        options['page_title'] = "Battle activity"
        self.render('stats/battle_activity.html', **options)


@route('/stats/battle-activity\.json$', name='stats_battle_activity_json')
class BattleActivityHandler(BaseHandler):

    def get(self):
        data = []
        solos = {}#defaultdict(int)
        multis = {}#defaultdict(int)
        computer = (self.db.User.collection
          .one({'username': settings.COMPUTER_USERNAME}))

        # the day the battle against computer was introduced
        june_21 = datetime.datetime(2011, 6, 21, 0, 0, 0)
        search = {'finished': {'$ne': None,
                               '$gte': june_21}}

        for each in self.db.Play.collection.find(search).sort('finished').limit(1):
            date = each['finished']
        for each in self.db.Play.collection.find(search).sort('finished', -1).limit(1):
            max_ = each['finished']

        jump = datetime.timedelta(days=1)
        while date < max_:
            timestamp = int(mktime(date.timetuple()))
            solos[timestamp] = 0
            multis[timestamp] = 0
            for play in (self.db.Play.collection
                         .find({'finished': {'$gte': date,
                                             '$lt': date + jump}})):
                if computer['_id'] in [x.id for x in play['users']]:
                    solos[timestamp] += 1
                else:
                    multis[timestamp] += 1
            date += jump

        solos = [dict(t=k, c=v) for (k, v) in solos.items()]
        multis = [dict(t=k, c=v) for (k, v) in multis.items()]
        #solos = sorted(solos, lambda x,y: cmp(x['t'], y['t']))
        #multis = sorted(multis, lambda x,y: cmp(x['t'], y['t']))
        self.write_json(dict(solos=solos, multis=multis))


@route('/stats/no-questions', name='stats_no_questions')
class NoQuestionsHandler(BaseHandler):

    def get(self):
        options = self.get_base_options()
        options['page_title'] = "Number of published questions"
        self.render('stats/no_questions.html', **options)


@route('/stats/no-questions\.json$', name='stats_no_questions_json')
class NoQuestionsDataHandler(BaseHandler):

    def get(self):
        data = []
        cumulative = self.get_argument('cumulative', False)
        contributors = {}#defaultdict(set)
        questions = {}#defaultdict(int)
        computer = (self.db.User.collection
          .one({'username': settings.COMPUTER_USERNAME}))

        # the day the battle against computer was introduced
        search = {'state': 'PUBLISHED'}
        #may_24 = datetime.datetime(2011, 5, 24, 0, 0, 0)
        #search['add_date'] = {'$gte': may_24}

        for each in self.db.Question.collection.find(search).sort('publish_date').limit(1):
            date = each['publish_date']
        for each in self.db.Question.collection.find(search).sort('publish_date', -1).limit(1):
            max_ = each['publish_date']

        jump = datetime.timedelta(days=7)
        _previous_questions = 0
        _previous_contributors = set()
        while date < max_:
            timestamp = int(mktime((date + jump).timetuple()))
            if cumulative:
                contributors[timestamp] = set(list(_previous_contributors))
                questions[timestamp] = _previous_questions
            else:
                contributors[timestamp] = set()
                questions[timestamp] = 0
            #print date.strftime('%d %b'), '--',
            #print (date + jump).strftime('%d %b'),
            for q in (self.db.Question.collection
                         .find({'state': 'PUBLISHED',
                                'publish_date': {'$gte': date,
                                                 '$lt': date + jump}})):
                questions[timestamp] += 1
                contributors[timestamp].add(q['author'].id)

                #if computer['_id'] in [x.id for x in play['users']]:
                #    contributors[timestamp] += 1
                #else:
                #    questions[timestamp] += 1
            #print questions[timestamp]
            _previous_questions = questions[timestamp]
            _previous_contributors = contributors[timestamp]
            date += jump

        contributors = [dict(t=k, c=len(v)) for (k, v) in contributors.items()]
        questions = [dict(t=k, c=v) for (k, v) in questions.items()]
        #contributors = sorted(contributors, lambda x,y: cmp(x['t'], y['t']))
        #questions = sorted(questions, lambda x,y: cmp(x['t'], y['t']))
        self.write_json(dict(contributors=contributors, questions=questions))

@route('/stats/no-questions-point.json$', name='stats_no_questions_point_json')
class NoQuestionsDataHandler(BaseHandler):

    def get(self):
        what = self.get_argument('what')
        timestamp = self.get_argument('timestamp')
        items = []
        if what == 'Questions':
            when = parse_datetime(timestamp)
            search = {'state': 'PUBLISHED',
                      'publish_date': {'$gte': when - datetime.timedelta(days=7),
                                       '$lt': when - datetime.timedelta(days=0)}}
            questions = (self.db.Question.collection
                         .find(search))
            #print "SEARCH", search
            for question in questions:
                #print question['_id']
                url = get_question_slug_url(question)
                items.append({'url': url,
                              'text': question['text']})

            #print "FOUND", len(items)
        elif what == 'Contributors':
            when = parse_datetime(timestamp)
            search = {'state': 'PUBLISHED',
                      'publish_date': {'$gte': when - datetime.timedelta(days=7),
                                       '$lt': when - datetime.timedelta(days=0)}}
            questions = (self.db.Question.collection
                         .find(search))
            #print "SEARCH", search
            users = defaultdict(int)
            for question in questions:
                users[question['author'].id] += 1
            as_list = [(c, i) for i, c in users.items()]
            as_list.sort()
            as_list.reverse()
            for count, _id in as_list:
                user = self.db.User.one({'_id': _id})
                text = "%s (%s)" % (user.username, count)
                items.append({'text': text})
        else:
            raise HTTPError(404, "Invalid argument %r" % what)
        self.write_json(dict(items=items))
