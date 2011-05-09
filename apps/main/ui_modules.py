import datetime
import tornado.web
import tornado.escape
from utils.timesince import smartertimesince
from utils import format_time_ampm
from utils.truncate import truncate_words
from utils.tornado_static import *

class Footer(tornado.web.UIModule):
    def render(self, user=None):
        return self.render_string("modules/footer.html",
          calendar_link=self.request.path != '/',
          user=user,
         )

class TruncateWords(tornado.web.UIModule):
    def render(self, string, max_words=20):
        return truncate_words(string, max_words)

class TruncateString(tornado.web.UIModule):
    def render(self, string, max_length=30):
        if len(string) > max_length:
            return string[:max_length] + '...'
        return string

class Settings(tornado.web.UIModule):
    def render(self, settings):
        return self.render_string("modules/settings.html",
           settings_json=tornado.escape.json_encode(settings),
           debug=self.handler.application.settings['debug']
         )

class TimeSince(tornado.web.UIModule):
    def render(self, date, date2=None):
        assert date
        return smartertimesince(date, date2)



class RenderText(tornado.web.UIModule):
    def render(self, text, format='plaintext'):
        if format == 'markdown':
            return markdown.markdown(text, safe_mode="escape")
        else:
            # plaintext
            html = '<p>%s</p>' % tornado.escape.linkify(text).replace('\n','<br>\n')

        return html


class _Link(dict):
    __slots__ = ('label','link','is_on')
    def __init__(self, label, link, is_on):
        self.label = label
        self.link = link
        self.is_on = is_on

class HelpSeeAlsoLinks(tornado.web.UIModule):
    def render(self):
        links = []
        current_path = self.request.path
        # add a is_on bool
        for each in self.handler.get_see_also_links():
            link = each['link']
            if not link.startswith('/help'):
                link = '/help' + link
            is_on = link == current_path
            links.append(dict(link=link,
                              label=each['label'],
                              is_on=is_on))

        return self.render_string("help/see_also.html",
          links=links
        )


class ShowUserName(tornado.web.UIModule):
    def render(self, user, first_name_only=False, anonymize_email=False):
        if first_name_only and user.first_name:
            name = user.first_name
        else:
            # because they might be None
            first_name = user.first_name and user.first_name or u''
            last_name = user.last_name and user.last_name or u''
            name = u'%s %s' % (first_name, last_name)
            name = name.strip()

        if not name:
            name = user.email
            if not name:
                name = "*Someone anonymous*"
            elif anonymize_email:
                name = name[:3] + '...@...' + name.split('@')[1][3:]
        return name

class ShowUser(ShowUserName):
    """one day make this with an image"""
    pass

class HelpPageTitle(tornado.web.UIModule):
    def render(self):
        links = []
        current_path = self.request.path
        for each in self.handler.get_see_also_links():
            link = each['link']
            if not link.startswith('/help'):
                link = '/help' + link
            if link == current_path:
                return each['label']

        return "Help on GKC"


class Messages(object):
    def __init__(self, msgs):
        self.msgs = msgs
    def as_list(self):
        return tornado.escape.json_encode(self.msgs)

class FlashMessages(tornado.web.UIModule):
    def render(self):
        msgs = []
        for message in self.handler.pull_flash_messages():
            msgs.append(dict(title=message.title,
                             text=message.text))
            message.read = True
            message.save()
        return Messages(msgs)

class SortKey(tornado.web.UIModule):
    def render(self, key):
        current_key = self.handler.get_argument('sort', '**')
        if current_key == key:
            if self.handler.get_argument('reverse', False):
                return "?sort=%s" % key
            else:
                return "?sort=%s&reverse=yes" % key
        else:
            return "?sort=%s" % key
