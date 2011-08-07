from time import sleep
from apps.main.models import connection
from apps.play.models import PlayPoints
from apps.rules.models import Rules

collection = connection.gkc[PlayPoints.__collection__]
rules_collection = connection.gkc[Rules.__collection__]
assert rules_collection.Rules.find({'default': True}).count()

search = {'rules':{'$exists': False}}

print "Fixing", collection.PlayPoints.find(search).count(), "objects"

default_rules = rules_collection.Rules.one({'default': True})._id
for each in collection.PlayPoints.find(search):
    each['rules'] = default_rules
    each.save()
