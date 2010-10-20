from tornado.web import HTTPError

def login_required(func):
    def is_logged_in(self):
        guid = self.get_secure_cookie('user')
        if guid:
            if self.db.users.User(dict(guid=guid)):
                return func(self)
        raise HTTPError(403, "Must be logged in")
    return is_logged_in