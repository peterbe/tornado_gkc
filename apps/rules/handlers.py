from pymongo.objectid import ObjectId
from apps.main.handlers import BaseHandler
from utils.routes import route, route_redirect
from utils.decorators import login_redirect, authenticated_plus
from utils import djangolike_request_dict
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


route_redirect('/rules$', '/rules/')
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
        core_rules = (self.db.Rules
                      .find({'author': None})
                      .sort('name'))

        options['all_rules'] = [
          ('Core', core_rules),
        ]
        options['editable'] = []
        if options['user'] and (self.db.Rules
                                .find({'author': options['user']._id})
                                .count()):
            your_rules = (self.db.Rules
                          .find({'author': options['user']._id})
                          .sort('name'))
            options['all_rules'].append(
               ('Your', your_rules),
            )

            for rules in self.db.Rules.find({'author': options['user']._id}):
                if self.can_edit_rules(rules, options['user']):
                    options['editable'].append(rules._id)

        self.render("rules/index.html", **options)


route_redirect('/rules/add$', '/rules/add/')
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
              "Your rules are not created and ready for play!")
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
