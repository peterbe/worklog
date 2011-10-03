import re
from cStringIO import StringIO
import datetime
from pymongo.objectid import InvalidId, ObjectId
import tornado.web
import logging
from email import Parser

from mongokit import ValidationError
from utils.decorators import login_required
from utils import parse_datetime, niceboolean, format_time_ampm
from tornado_utils.routes import route
from apps.main.handlers import BaseHandler, EventsHandler
from apps.main.config import MINIMUM_DAY_SECONDS
from models import EmailReminder
from utils.send_mail import send_email
from reminder_utils import ParseEventError, parse_time, \
  parse_duration, parse_email_line
from settings import EMAIL_REMINDER_SENDER, EMAIL_REMINDER_NOREPLY
from tornado_utils.timesince import smartertimesince


@route('/emailreminders/$')
class EmailRemindersHandler(BaseHandler):

    def get(self):
        options = self.get_base_options()

        weekdays = list(EmailReminder.WEEKDAYS)
        monday_first = False

        edit_reminder = self.get_edit_reminder()

        # default
        options['weekday_reminders'] = dict()
        options['count_reminders'] = 0
        options['all_reminder_classnames'] = dict()
        options['email_reminders_addresses'] = list()

        background_colors = iter(("#ff5800", "#0085cc",
                    "#c747a3","#26B4E3", "#bd70c7", "#cddf54", "#FBD178" ))

        email_reminder_ids = set()
        user = self.get_current_user()
        if user:
            _base_search = {'user': user._id}
            weekday_reminders = dict()
            for weekday in EmailReminder.WEEKDAYS:
                _reminders = self.db.EmailReminder\
                  .find(dict(_base_search, weekdays=weekday))

                weekday_reminders[weekday] = _reminders.sort('time')
                options['count_reminders'] += _reminders.count()

            for each in self.db.EmailReminder.find(_base_search):
                options['email_reminders_addresses'].append(
                  EMAIL_REMINDER_SENDER % {'id':each._id}
                )
            options['weekday_reminders'] = weekday_reminders

            user_settings = self.db.UserSettings.one({'user.$id': user._id})
            if user_settings:
                monday_first = user_settings.monday_first

            for reminder in self.db.EmailReminder.find(_base_search):
                options['all_reminder_classnames'][str(reminder._id)] = \
                  background_colors.next()

        if not monday_first:
            # make it start with the Sunday
            weekdays.insert(0, weekdays[-1])
            weekdays.pop()

        options['weekdays'] = weekdays

        options['all_reminder_classnames'] = options['all_reminder_classnames'].items()
        options['edit_reminder'] = edit_reminder

        self.render('emailreminders/index.html', **options)

    def get_edit_reminder(self):
        edit_reminder = None
        #print 'self.get_current_user()', self.get_current_user()
        if self.get_argument('edit', None):
            user = self.get_current_user()
            if not user:
                raise tornado.web.HTTPError(403, "not logged in")

            try:
                edit_reminder = self.db.EmailReminder\
                  .one({'_id': ObjectId(self.get_argument('edit'))})
            except InvalidId:
                raise tornado.web.HTTPError(400, "Invalid ID")

            if not edit_reminder:
                raise tornado.web.HTTPError(404, "Not found")

            if edit_reminder.user._id != user._id:
                raise tornado.web.HTTPError(404, "Not yours")

        return edit_reminder


    @login_required
    def post(self):
        edit_reminder = self.get_edit_reminder()
        if edit_reminder:
            if self.get_argument('delete', False):
                edit_reminder.delete()
                return self.redirect('/emailreminders/')

        weekdays = self.get_arguments('weekdays')
        assert isinstance(weekdays, list), type(weekdays)
        time_hour = int(self.get_argument('time_hour'))
        time_minute = int(self.get_argument('time_minute'))
        tz_offset = float(self.get_argument('tz_offset'))
        instructions_or_summary = self.get_argument('instructions_or_summary', None)

        user = self.get_current_user()
        if edit_reminder:
            email_reminder = edit_reminder
        else:
            email_reminder = self.db.EmailReminder()
            email_reminder.user = user._id
        email_reminder.weekdays = weekdays
        email_reminder.time = (time_hour, time_minute)
        email_reminder.tz_offset = tz_offset
        email_reminder.set_next_send_date()
        if instructions_or_summary == 'instructions':
            email_reminder.include_instructions = True
            email_reminder.include_summary = False
        elif instructions_or_summary == 'both':
            email_reminder.include_instructions = True
            email_reminder.include_summary = True
        elif instructions_or_summary == 'summary':
            email_reminder.include_instructions = False
            email_reminder.include_summary = True
        try:
            email_reminder.save()
        except ValidationError, msg:
            raise tornado.web.HTTPError(400, str(msg))

        # XXX: flash message?
        self.redirect('/emailreminders/')


@route('/emailreminders/send/$')
class SendEmailRemindersHandler(BaseHandler):
    """Can be fired from a cronjob every 15 minutes without having to be worried
    about accidentally sending the same user the same email. A log is used to
    safeguard against possible duplicate sendings.
    """

    def get(self):
        # this should perhaps use a message queue instead
        now_utc = datetime.datetime.utcnow()
        dry_run = niceboolean(self.get_argument('dry_run', False))
        if self.get_argument('now_utc', None):
            now_utc = parse_datetime(self.get_argument('now_utc'))

        search = dict(_next_send_date={'$lte':now_utc})
        for email_reminder in self.db.EmailReminder.find(search):
            self.write("TO: %s\n" % email_reminder.user.email)
            # the reason we're including the now date is so that we can
            # A) make a dry run on a specific date and B) override what "now"
            # is for unit tests.
            self._send_reminder(email_reminder, now_utc, dry_run=dry_run)

            if not dry_run:
                email_reminder.set_next_send_date(now_utc)
                email_reminder.save()

                email_reminder_log = self.db.EmailReminderLog()
                email_reminder_log.email_reminder = email_reminder
                email_reminder_log.save()

        self.write("Done\n")

    def _send_reminder(self, email_reminder, now, dry_run=False):

        subject = u"[DoneCal]"
        if email_reminder.time[0] > 12:
            about_today = True
            subject += " What did you do today?"
        else:
            about_today = False
            subject += u" What did you do yesterday?"

        first_name = email_reminder.user.first_name

        email_reminder_edit_url = 'http://%s/emailreminders/' % self.request.host
        if email_reminder.user.premium:
            email_reminder_edit_url = email_reminder_edit_url\
              .replace('http://','https://')

        hour_example_1 = '14:45'
        hour_example_2 = '10:30'
        user_settings = self.get_current_user_settings(user=email_reminder.user)
        if user_settings and user_settings.ampm_format:
            hour_example_1 = '2pm'
            hour_example_2 = '10:30am'

        summary_events = list()
        if email_reminder.include_summary:
            _search = {'user.$id': email_reminder.user._id}
            # if it was about today, make the search start at 00.00 today
            _today = datetime.datetime(now.year, now.month, now.day)
            if about_today:
                _search['start'] = {'$gte': _today}
            else:
                _yesterday = _today - datetime.timedelta(days=1)
                _search['start'] = {'$gte': _yesterday, '$lt':_today}

            for event in self.db.Event.find(_search).sort('start', 1):
                summary_events.append(self._summorize_event(event))

        email_reminder_edit_url += '?edit=%s' % email_reminder._id
        body = self.render_string("emailreminders/send_reminder.txt",
                                  email_reminder=email_reminder,
                                  first_name=first_name,
                                  about_today=about_today,
                                  email_reminder_edit_url=\
                                  email_reminder_edit_url,
                                  hour_example_1=hour_example_1,
                                  hour_example_2=hour_example_2,
                                  include_instructions=email_reminder.include_instructions,
                                  summary_events=summary_events)

        from_email = EMAIL_REMINDER_SENDER % {'id': str(email_reminder._id)}
        from_ = "DoneCal <%s>" % from_email
        send_email(self.application.settings['email_backend'],
                   subject,
                   body,
                   from_,
                   [email_reminder.user.email],
                   )

    def _summorize_event(self, event):
        """return a one-line summary of the event"""
        user_settings = self.get_user_settings(event.user)
        ampm_format = user_settings and user_settings.get('ampm_format', False) or False

        line = u''
        if event.all_day:
            line += u"(All day) "
        else:
            duration = smartertimesince(event.start, event.end)
            line += u"(%s, %s) " % (format_time_ampm(event.start), duration)
        return line + event.title



@route('/emailreminders/receive/$')
class ReceiveEmailReminder(EventsHandler):
    def check_xsrf_cookie(self):
        pass

    def post(self):
        try:
            self._post()
        except:
            logging.error("Failed to receive post", exc_info=True)
            raise

    def _post(self):

        if self.request.body:
            message = self.request.body
        else:
            message = self.get_argument('message')

        parser = Parser.Parser()
        msg = parser.parsestr(message)

        ## Check that it's sent to the right address
        email_tos = parse_email_line(msg['To'])
        email_reminder = None
        # need to turn then reply to address into a regex
        reply_to_parts = EMAIL_REMINDER_SENDER % dict(id='XXX')
        reply_to_parts = reply_to_parts.split('XXX')
        assert len(reply_to_parts) == 2
        regex = re.compile(re.escape(reply_to_parts[0]) + '(\w+)' \
          + re.escape(reply_to_parts[1]), re.I)
        for email_to in email_tos:
            if regex.findall(email_to):
                _id = regex.findall(email_to)[0]
                try:
                    email_reminder = self.db.EmailReminder\
                      .one({'_id': ObjectId(_id)})
                except InvalidId:
                    pass

        ## Check that it was sent from someone we know
        from_user = None
        for from_email in parse_email_line(msg['From']):
            from_user = self.find_user(from_email)

        message_body = None
        character_set = 'utf-8'
        if msg.is_multipart():
            for part in msg.walk():
                if part.is_multipart():
                    continue
                name = part.get_param('name')
                if not part.get_param('name') and part.get_content_type().lower() == 'text/plain':
                    message_body = part.get_payload(decode=True)
                    if isinstance(message_body, str):
                        for charset in part.get_charsets():
                            if not charset:
                                charset = 'utf8'
                            message_body = unicode(message_body, charset)
                            character_set = charset
                            break
                    #print "BODY"
                    #print repr(message_body)
                    #print message_body
                    # If it's a multipart email, only use the first part
                    break


        else:
            # not a multipart message then it's easy
            message_body = msg.get_payload(decode=True)
            for each in msg.get_charsets():
                if each:
                    character_set = each
                    break
            if character_set:
                message_body = unicode(message_body, character_set)
            else:
                message_body = unicode(message_body, 'utf-8')

        if not from_user:
            # only bother to reply if the email appears to be sent from
            # us originally
            if 'INSTRUCTIONS' in message_body and 'DoneCal' in msg['Subject']:
                self.error_reply("Not a registered account: %s" % msg['From'], msg, message_body)

            self.write("Not recognized from user (%r)" % msg['From'])
            return

        assert from_user

        if not email_reminder:
            # At this point, we know it was not a proper reply,
            # but it was sent from one of our users because otherwise it would have been
            # dealt with just above this
            err_msg = u"This is not a reply to an email reminder from your account.\n"\
                      u"To set some up, go to http://%s/emailreminders/" % \
                      self.request.host
            self.error_reply(err_msg, msg, message_body)

            self.write("Not a reply to an email reminder")
            return

        assert email_reminder

        if email_reminder.user._id != from_user._id:
            if 'INSTRUCTIONS' in message_body \
              and 'DoneCal' in msg['Subject']:
                owner_email = email_reminder.user.email
                p = owner_email.find('@')
                owner_email_brief = owner_email[:p-2] + '...' + owner_email[p+2:]
                err_msg = u"This is a reply to someone else's email reminder "\
                          u"that belonged to: %s" % owner_email_brief
                self.error_reply(err_msg, msg, message_body, email_reminder=email_reminder)

            self.write("No email reminders set up")
            return

        CRLF = '\r\n'
        # formatflowed expects the line breakers to be \r\n
        if not message_body.count(CRLF):
            message_body = message_body.replace('\n', CRLF)
        original_message_lines = [x for x in message_body.splitlines()
                                  if x.startswith('> ')]
        if not original_message_lines:
            # then desperately look for something like
            # ------Mensaje original------
            new_text = []
            for line in message_body.splitlines():
                if line.startswith('------') and line.endswith('------'):
                    break
                new_text.append(line)
            else:
                err_msg = u"Your email is not a reply to an email reminder. "\
                          u"When sending your reply try to use inline style."
                self.error_reply(err_msg, msg, message_body)
                self.write("Not a reply email")
                return
            remove_last_paragraph = False
        else:
            remove_last_paragraph = True
            message_body_ascii = message_body.encode(character_set)
            from formatflowed import decode
            try:
                if character_set:
                    textflow = decode(message_body_ascii, character_set=character_set)
                else:
                    textflow = decode(message_body_ascii)
            except LookupError:
                if not character_set:
                    raise
                # _character_set is quite likly 'iso-8859-1;format=flowed'
                _character_set = _character_set.split(';')[0].strip()
                textflow = decode(message_body_ascii, character_set=character_set)

            new_text = []
            for segment in textflow:
                if not segment[0]['quotedepth']:
                    # level zero
                    new_text.append(segment[1])
                else:
                    break

        new_text = u"\n".join(new_text)
        if email_reminder:
            if email_reminder.time[0] > 12:
                about_today = True
            else:
                about_today = False
        else:
            if 'today' in msg['Subject']:
                about_today = True
            else:
                about_today = False

        tz_offset = email_reminder.tz_offset
        count_new_events = 0
        paragraphs = re.split('\n\n+', new_text.strip())
        if remove_last_paragraph:
            # Because we expect the last line to be something like
            #    On 25 December 2010 09:00, DoneCal
            #    <reminder+4d11e7d674a1f8360a000078@donecal.com> wrote:
            #
            # So we have to remove it.
            paragraphs = paragraphs[:-1]
        previous_duration = None
        for text in paragraphs:
            if not text.strip():
                # it was blank
                continue
            try:
                event = self.parse_and_create_event(from_user, text, about_today, tz_offset,
                                                    previous_duration=previous_duration)
                if event:
                    if not event.all_day:
                        previous_duration = (event.end - event.start).seconds / 60
                    self.write("Created %r\n" % event.title)
                    count_new_events += 1
            except ParseEventError, exception_message:
                self.write("Parse event error (%s)\n" % exception_message)
                if 'INSTRUCTIONS' in message_body and \
                 'DoneCal' in msg['Subject']:
                    err_msg = "Failed to create an event from this line:\n\t%s\n" \
                      % text
                    err_msg += "(Error message: %s)\n" % exception_message
                    self.error_reply(err_msg, msg, message_body, email_reminder=email_reminder)
                else:
                    logging.error("Parse event error on email not replied to", exc_info=True)

        self.write("\n")

    def parse_and_create_event(self, user, text, about_today, tz_offset,
                               previous_duration=None):
        """parse the text (which can be more than one line) and return either a
        newly created event object or nothing.
        """
        text, time_ = parse_time(text)
        text, duration = parse_duration(text)
        if not time_ and duration:
            # if tz_offset is -5.5 we want the time to become
            # (17, 30), not (17.5, 0)
            tz_offset_minutes = tz_offset * 60
            tz_offset_h = int(tz_offset_minutes) / 60
            tz_offset_m = int(tz_offset_minutes) % 60
            if tz_offset_h > 0:
                tz_offset_h -= 1
            else:
                if tz_offset_h:
                    tz_offset_h += 1
                if tz_offset_h:
                    tz_offset_m *= -1
            # default is at 12.00 if no time was specified
            first_hour = 12
            user_settings = self.get_user_settings(user, fast=True)
            if user_settings:
                first_hour = user_settings['first_hour']
            time_ = (first_hour - tz_offset_h, 0 - tz_offset_m)

        text = text.strip()

        if len(text.splitlines()) > 1:
            title = text.splitlines()[0]
            description = '\n'.join(text.splitlines()[1:])
        else:
            title = text
            description = u''

        if time_:
            all_day = False
        else:
            all_day = True

        if about_today:
            start_base = datetime.datetime.today()
        else:
            start_base = datetime.datetime.today() - datetime.timedelta(days=1)

        if all_day:
            start = end = start_base
        else:
            if previous_duration:

                duration_hours = int(previous_duration) / 60
                duration_minutes = int(previous_duration) % 60
                if isinstance(time_, tuple):
                    time_ = list(time_)
                time_[0] += duration_hours
                time_[1] += duration_minutes

            if time_[1] == 60:
                time_[0] += 1
                time_[1] = 0

            start = start_base
            start = datetime.datetime(start.year, start.month, start.day,
                                      time_[0], time_[1])
            if not duration:
                duration = MINIMUM_DAY_SECONDS / 60
            end = start + datetime.timedelta(minutes=duration)

        if isinstance(title, str):
            try:
                title = title.decode("utf-8")
            except UnicodeDecodeError:
                raise ParseEventError("Title not a valid UTF-8 string")

        if isinstance(description, str):
            try:
                description = description.decode("utf-8")
            except UnicodeDecodeError:
                raise ParseEventError("Description not a valid UTF-8 string")

        event, not_duplicate = self.create_event(
          user,
          title=title,
          description=description,
          all_day=all_day,
          start=start,
          end=end,
        )

        return event


    def error_reply(self, error_message, msg, body, email_reminder=None):
        """send an email reply"""
        if isinstance(body, str):
            body = unicode(body, 'utf-8')

        body = body.replace('\r\n', '\n')
        body = '\n'.join(['> %s' % line for line in body.splitlines()])
        body = u'Error in receiving email.\n   %s\n\nPlease try again.\n\n' \
          % error_message + body
        subject = "Re: %s" % msg['Subject']

        if email_reminder:
            from_email = EMAIL_REMINDER_SENDER % {'id': str(email_reminder._id)}
        else:
            from_email = EMAIL_REMINDER_NOREPLY
        from_ = "DoneCal <%s>" % from_email

        send_email(self.application.settings['email_backend'],
                   subject,
                   body,
                   from_,
                   [msg['From']],
                   )

        #self.error_reply("Not a registered account: %s" % msg['From'], msg)
