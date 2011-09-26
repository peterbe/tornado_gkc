#!/usr/bin/env python
import here
import datetime
import tornado.options
from tornado.options import define, options
import settings

define("verbose", default=False, help="be louder", type=bool)
define("all", default=False, help="purge all", type=bool)
define("users", default=5, help="no. recent plays", type=int)
#define("random", default=False, help="pick random users", type=bool)

def main(*args):
    tornado.options.parse_command_line()
    from apps.main.models import User, connection
    import apps.play.models # so they get registered
    import apps.questions.models # so they get registered

    db = connection.gkc
    if options.all:
        max_users = 999999
    else:
        max_users = options.users

    def delete_user(user):
        assert user.anonymous
        assert not db.Question.find({'author.$id': user._id}).count()
        search = {'user.$id': user._id}
        slim_search = {'user': user._id}
        assert not db.QuestionReview.find(search).count()

        for qp in db.QuestionPoints.find(search):
            qp.delete()
            if options.verbose:
                print "\tdelete question points"

        for us in db.UserSettings.find(slim_search):
            us.delete()
            if options.verbose:
                print "\tdelete settings"

        for fm in db.FlashMessage.find(slim_search):
            fm.delete()
            if options.verbose:
                print "\tdelete flash message"

        for qp in db.PlayPoints.find(search):
            qp.delete()
            if options.verbose:
                print "\tdelete play points"

        for p in db.Play.find({'users.$id': user._id}):
            p.delete()
            if options.verbose:
                print "\tdelete play"

        user.delete()
        if options.verbose:
            print "delete", user.username


    computer = (db.User.collection
          .one({'username': settings.COMPUTER_USERNAME}))

    MIN_AGE = 1
    today = datetime.datetime.today()
    then = today - datetime.timedelta(days=MIN_AGE)
    users = db.User.find({
      'anonymous': True,
      'add_date': {'$lt': then}
    }).sort('add_date')
    count = 0
    if options.verbose:
        print users.count(), "anonymous users"
    for user in users:
        plays = db.Play.find({'users.$id': user._id})
        if not plays.count():
            delete_user(user)
            count += 1
            continue

        _break = False
        for play in plays:
            other_users = [x for x in play.users
                           if x != user]

            if [x for x in other_users if x._id != computer['_id']]:
                # don't want to delete plays where a real user has played
                _break = True
                print "Played against against a real user"
                break
        if _break:
            # can't delete this user because it has played real
            # battles against real users
            continue

        # all plays were against computers
        delete_user(user)
        count += 1

        if count >= max_users:
            break


if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
