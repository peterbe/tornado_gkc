from bson.objectid import ObjectId, InvalidId
from apps.main.handlers import BaseHandler
from tornado_utils.routes import route
from tornado.web import HTTPError
from utils.decorators import login_redirect, authenticated_plus
from tornado_utils import djangolike_request_dict
from forms import RulesForm

class BaseRulesHandler(BaseHandler):

    def get_all_published_genre_choices(self):
        choices = []
        for genre in self.db.Genre.find({'approved': True}).sort('name'):
            count = self.db.Question.find({'genre.$id': genre._id,
                                           'state': 'PUBLISHED'}).count()
            label = '%s (%s)' % (genre.name, count)
            choices.append((str(genre._id), label))
        return choices

    def can_edit_rules(self, rules, user):
        if not self.db.Play.find({'rules': rules._id}).count():
            if self.is_admin_user(user):
                return True
            if rules.author == user:
                return True
        return False

    def find_rules(self, _id):
        if isinstance(_id, basestring):
            try:
                _id = ObjectId(_id)
            except InvalidId:
                return None
        return self.db.Rules.one({'_id': _id})

    def must_find_rules(self, _id, user):
        rules = self.find_rules(_id)
        if not rules:
            raise HTTPError(404, "Not found")
        if rules.author != user:
            if not self.is_admin_user(user):
                raise HTTPError(403, "Forbidden")
        return rules

    def count_playable_questions(self, rules, genres=None, pictures_only=None):
        if genres is None:
            genres = rules['genres']
        if pictures_only is None:
            pictures_only = rules['pictures_only']
        search = {'state': 'PUBLISHED'}
        if genres:
            if isinstance(genres[0], basestring):
                genre_ids = []
                for _id in genres:
                    try:
                        genre = self.db.Genre.collection.one({'_id': ObjectId(_id)})
                    except InvalidId:
                        genre = None
                    if not genre:
                        raise HTTPError(400, "Invalid genre %r" % _id)
                    genre_ids.append(genre['_id'])
            else:
                genre_ids = genres
            search['genre.$id'] = {'$in': genre_ids}
        if pictures_only:
            questions_with_pictures = []
            for question_image in self.db.QuestionImage.collection.find():
                questions_with_pictures.append(question_image['question'].id)
            search['_id'] = {'$in': questions_with_pictures}
        questions = self.db.Question.collection.find(search)

        result = {
          'questions': questions.count(),
          'with_knowledge': 0,
        }
        if result['questions']:
            question_ids = [x['_id'] for x in questions]
            search = {'question.$id': {'$in': question_ids}}
            knowledges = self.db.QuestionKnowledge.find(search)
            result['with_knowledge'] = knowledges.count()

        return result


@route('/rules/$', name='rules')
class RulesHomeHandler(BaseRulesHandler):

    def get(self):
        options = self.get_base_options()
        options['page_title'] = "Rules"
        if not self.db.Rules.find().count():
            default = self.db.Rules()
            default.name = u"Default rules"
            default.default = True
            default.save()
        search = {'author': None}
        core_rules = (self.db.Rules
                      .find(search)
                      .sort('name'))

        counts = {}
        for rule in self.db.Rules.collection.find(search):
            counts[rule['_id']] = self.count_playable_questions(rule)

        options['all_rules'] = [
          ('Core', core_rules),
        ]

        options['editable'] = []
        your_rule_ids = []
        if options['user'] and (self.db.Rules
                                .find({'author': options['user']._id})
                                .count()):
            search = {'author': options['user']._id}
            your_rules = (self.db.Rules
                          .find(search)
                          .sort('name'))
            options['all_rules'].append(
               ('Your', your_rules),
            )
            for rule in self.db.Rules.collection.find(search):
                counts[rule['_id']] = self.count_playable_questions(rule)
                your_rule_ids.append(rule['_id'])

            for rules in self.db.Rules.find(search):
                if self.can_edit_rules(rules, options['user']):
                    options['editable'].append(rules._id)

        if options['user']:
            default_rules_id = self.db.Rules.one({'default': True})._id
            played_rule_ids = []
            not_rule_ids = [default_rules_id] + your_rule_ids
            for p in (self.db.Play.collection
                      .find({'users.$id': options['user']._id,
                             'rules': {'$nin': not_rule_ids}})):
                played_rule_ids.append(p['rules'])
            search = {'_id': {'$in': played_rule_ids}}

            for rule in self.db.Rules.collection.find(search):
                counts[rule['_id']] = self.count_playable_questions(rule)

            played_rules = (self.db.Rules
                            .find(search)
                            .sort('name'))
            if played_rules.count():
                options['all_rules'].append(
                  ('Played', played_rules)
                )

        options['playable_questions'] = counts
        self.render("rules/index.html", **options)


@route('/rules/(\w{24})$', name='rules_page')
class RulesPageHandler(BaseRulesHandler):
    def get(self, _id):
        options = self.get_base_options()
        rules = self.find_rules(_id)
        #self.write(rules.name)

        options['page_title'] = rules.name
        options['is_editable'] = False #XXX
        options['rule'] = rules
        options['playable_questions'] = {
          rules._id: self.count_playable_questions(rules)
        }
        self.render("rules/rule.html", **options)

@route('/rules/add/$', name='rules_add')
class AddRulesHandler(BaseRulesHandler):

    @authenticated_plus(lambda u: not u.anonymous)
    def get(self, form=None):
        options = self.get_base_options()
        if form is None:
            form = RulesForm(no_questions=10,
                             thinking_time=15,
                             min_no_people=2,
                             max_no_people=2,
                             )
            form.set_genre_choices(self.get_all_published_genre_choices())
        options['form'] = form
        options['page_title'] = "Add your own rules"
        self.render("rules/add.html", **options)

    @authenticated_plus(lambda u: not u.anonymous)
    def post(self):
        user = self.get_current_user()
        data = djangolike_request_dict(self.request.arguments)
        form = RulesForm(data)
        form.set_genre_choices(self.get_all_published_genre_choices())

        if form.validate():
            genres = []
            for id_str in form.genres.data:
                genres.append(self.db.Genre.one({'_id': ObjectId(id_str),
                                                 'approved': True})._id)
            rules = self.db.Rules()
            rules.name = form.name.data
            rules.no_questions = form.no_questions.data
            rules.thinking_time = form.thinking_time.data
            rules.min_no_people = form.min_no_people.data
            rules.max_no_people = form.max_no_people.data
            rules.genres = genres
            rules.notes = form.notes.data
            rules.author = user._id
            rules.default = False
            rules.pictures_only = form.pictures_only.data
            rules.alternatives_only = form.alternatives_only.data
            rules.save()

            self.push_flash_message("Rules added",
              "Your rules are now created and ready for play!")
            goto_url = self.reverse_url('rules')

            self.redirect(goto_url)
        else:
            self.get(form=form)

@route('/rules/(\w{24})/delete/$', name='rules_delete')
class DeleteRulesHandler(BaseRulesHandler):

    @authenticated_plus(lambda u: not u.anonymous)
    def get(self, _id, form=None):
        options = self.get_base_options()
        rules = self.must_find_rules(_id, options['user'])
        if not self.can_edit_rules(rules, options['user']):
            raise HTTPError(403, "Can't edit these rules")

        self.render('rules/delete.html', **options)

    @authenticated_plus(lambda u: not u.anonymous)
    def post(self, _id):
        user = self.get_current_user()
        rules = self.must_find_rules(_id, user)
        if not self.can_edit_rules(rules, user):
            raise HTTPError(403, "Can't edit these rules")


@route('/rules/(\w{24})/edit/$', name='rules_edit')
class EditRulesHandler(BaseRulesHandler):

    @authenticated_plus(lambda u: not u.anonymous)
    def get(self, _id, form=None):
        options = self.get_base_options()
        rules = self.must_find_rules(_id, options['user'])
        if not self.can_edit_rules(rules, options['user']):
            raise HTTPError(403, "Can't edit these rules")
        options['rules'] = rules
        if form is None:
            initial = dict(rules)
            #initial['spell_correct'] = question.spell_correct
            #initial['genre'] = question.genre.name
            form = RulesForm(**initial)
            form.set_genre_choices(self.get_all_published_genre_choices())
        options['form'] = form
        options['page_title'] = "Edit rules"
        self.render('rules/edit.html', **options)

    @authenticated_plus(lambda u: not u.anonymous)
    def post(self, _id):
        user = self.get_current_user()
        rules = self.must_find_rules(_id, user)
        if not self.can_edit_rules(rules, user):
            raise HTTPError(403, "Can't edit these rules")
        data = djangolike_request_dict(self.request.arguments)
        form = RulesForm(data)
        form.set_genre_choices(self.get_all_published_genre_choices())

        if form.validate():
            genres = []
            for id_str in form.genres.data:
                genres.append(self.db.Genre.one({'_id': ObjectId(id_str),
                                                 'approved': True})._id)
            rules.name = form.name.data
            rules.no_questions = form.no_questions.data
            rules.thinking_time = form.thinking_time.data
            rules.min_no_people = form.min_no_people.data
            rules.max_no_people = form.max_no_people.data
            rules.genres = genres
            rules.notes = form.notes.data
            rules.pictures_only = form.pictures_only.data
            rules.alternatives_only = form.alternatives_only.data
            rules.save()

            edit_url = self.reverse_url('rules_edit', rules._id)

            self.push_flash_message("Rules edited!",
                 "Rules are ready to be played")

            self.redirect(edit_url)

        else:
            self.get(_id, form=form)

@route('/rules/playable_questions.json$', name='playable_questions_json')
class PlayableQuestionsHandler(BaseRulesHandler):

    def get(self):
        user = self.get_current_user()
        if not user or (user and user.anonymous):
            raise HTTPError(403, "Forbidden")
        result = {}
        if 'genres[]' in self.request.arguments:
            genres = self.get_arguments('genres[]')
        else:
            genres = self.get_arguments('genres')
        pictures_only = self.get_argument('pictures_only', False)
        result = self.count_playable_questions(None, genres=genres, pictures_only=pictures_only)
        self.write_json(result)
