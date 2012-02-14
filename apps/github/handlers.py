import datetime
import os
from urlparse import urlparse
from pymongo.objectid import ObjectId, InvalidId
import isodate
import tornado.web
import tornado.ioloop
from apps.main.handlers import BaseHandler
from tornado_utils.routes import route, route_redirect


@route('/github/pull/')
class GithubPullHandler(BaseHandler):

    ROOT_CLONES_DIRECTORY = '/tmp'

    @tornado.web.asynchronous
    def get(self):
        if self.get_argument('url', None):
            full_url = self.get_argument('url').strip()
            parsed = urlparse(full_url)
            if not parsed.netloc == 'github.com':
                raise tornado.web.HTTPError(404, "Must be a github.com repo")
            username = parsed.path.split('/')[1]
            repo = parsed.path.split('/')[2]
            if repo.endswith('.git'):
                repo = repo[:-4]
            if '/tree/' in parsed.path:
                branch = parsed.path.split('/')[4]
            else:
                branch = None
            github_repo = self.db.GitHubRepo.find_one({
              'username': username,
              'repo': repo,
              'branch': branch,
            })
            if not github_repo:
                github_repo = self.db.GitHubRepo()
                github_repo.username = username
                github_repo.repo = repo
                if branch:
                    github_repo.branch = branch

            user_dir = os.path.join(self.ROOT_CLONES_DIRECTORY, username)
            if not os.path.isdir(user_dir):
                os.mkdir(user_dir)
            dest_dir = os.path.join(user_dir, repo)
            if not os.path.isdir(dest_dir):
                cmd = 'git clone -n --bare '
                if branch:
                    cmd += '-b "%s" ' % branch
                cmd += '%s %s' % (full_url, dest_dir)
            else:
                raise NotImplementedError
            self.ioloop = tornado.ioloop.IOLoop.instance()
            self.pipe = p = os.popen(cmd)
            self.ioloop.add_handler(
              p.fileno(),
              self.async_callback(lambda fd, events: self.on_response(fd, events, github_repo)),
              self.ioloop.READ
            )
        else:
            username = self.get_argument('username')
            repo = self.get_argument('repo')
            branch = self.get_argument('branch', None)

    def on_response(self, fd, events, github_repo):
        for line in self.pipe:
            self.write(line)

        github_repo.last_pull_date = datetime.datetime.utcnow()
        github_repo.save()
        self.write("ID: %s\n" % github_repo._id)

        self.ioloop.remove_handler(fd)
        self.finish()


@route('/github/(\w{24})/load/')
class GithubLoadHandler(GithubPullHandler):

    @tornado.web.asynchronous
    def get(self, _id):
        try:
            github_repo = self.db.GitHubRepo.find_one({'_id': ObjectId(_id)})
            assert github_repo
        except (InvalidId, AssertionError):
            raise tornado.web.HTTPError(404, "Not found")


        user_dir = os.path.join(self.ROOT_CLONES_DIRECTORY, github_repo.username)
        dest_dir = os.path.join(user_dir, github_repo.repo)
        assert os.path.isdir(dest_dir)

        cmd = 'cd %s; ' % dest_dir
        cmd += 'git log '
        if github_repo.branch:
            cmd += github_repo.branch
        else:
            cmd += 'master'
        cmd += ' --date=iso --pretty=format:"%h%x09%an%x09%ad%x09%s"'

        self.ioloop = tornado.ioloop.IOLoop.instance()
        self.pipe = p = os.popen(cmd)
        self.ioloop.add_handler(
          p.fileno(),
          self.async_callback(lambda fd, events: self.on_response(fd, events, github_repo)),
          self.ioloop.READ
        )

    def on_response(self, fd, events, github_repo):
        self.set_header('Content-Type', 'text/plain')
        _github_base_url = (u'https://github.com/%s/%s/commit/' %
                            (github_repo.username, github_repo.repo))

        _username = u'%s/%s' % (github_repo.username, github_repo.repo)
        user = self.db.User.find_one({'username': _username})
        if not user:
            user = self.db.User()
            user.username = _username
            user.first_name = u'Github'
            user.last_name = _username
            user.save()

        for line in self.pipe:
            hash, user_name, date, message = line.split('\t', 5)
            message = message.strip()
            date = isodate.parse_datetime(date.replace(' ', 'T', 1))
            start = date
            end = start + datetime.timedelta(minutes=30)
            external_url = _github_base_url + hash
            description = unicode(message.strip(), 'utf-8')
            title = unicode(user_name, 'utf-8')
            search = {
              'user': user,
              'title': title,
              'start': start,
              'external_url': external_url,
              }
            event = self.db.Event.find_one(search)
            if not event:
                event = self.db.Event()
                event.user = user
                event.title = title
                event.start = start
                event.end = end
                event.external_url = external_url
                event.description = description
                event.all_day = False
                event.save()

            self.write(line)

        share = self.db.Share.find_one({'user': user._id})
        if not share:
            share = self.db.Share()
            share.user = user._id
            # might up this number in the future
            share.save()
        share_url = "/share/%s" % share.key
        full_share_url = '%s://%s%s' % (self.request.protocol,
                                        self.request.host,
                                        share_url)
        self.write('\n%s\n' % full_share_url)

        #github_repo.last_pull_date = datetime.datetime.utcnow()
        #github_repo.save()

        self.ioloop.remove_handler(fd)
        self.finish()
