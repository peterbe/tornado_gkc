from time import sleep
from apps.main.models import connection
from apps.play.models import Play
from apps.rules.models import Rules
print

collection = connection.gkc[Play.__collection__]
rules_collection = connection.gkc[Rules.__collection__]
#assert rules_collection.Rules.find({'default': True}).count()

search = {'rules':{'$exists': False}}
#search = {'rules':None}

print "Fixing", collection.Play.find(search).count(), "objects"

default_rules = rules_collection.Rules.one({'default': True})._id
for each in collection.Play.find(search):
    each['rules'] = default_rules
    each.save()
