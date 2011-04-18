from urllib import quote as url_quote
from tornado.web import HTTPError

def login_required(func, redirect_to=None):
    def is_logged_in(self):
        guid = self.get_secure_cookie('user')
        if guid:
            if self.db.users.User(dict(guid=guid)):
                return func(self)
        if redirect_to:
            next = self.request.path
            if self.request.query:
                next += '?%s' % self.request.query
            url = redirect_to + '?next=%s' % url_quote(next)
            self.redirect(url)
        else:
            raise HTTPError(403, "Must be logged in")
    return is_logged_in

def login_redirect(func):
    return login_required(func, redirect_to='/login/')
