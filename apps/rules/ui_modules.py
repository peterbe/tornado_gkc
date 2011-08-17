import time
from pprint import pprint
from collections import defaultdict
import tornado.web

class RulesFacts(tornado.web.UIModule):
    def render(self, rule, counts):
        options = {
          'rule': rule,
          'counts': counts,
        }

        return self.render_string('rules/rules_facts.html', **options)


_times_cache = {}

class RulesStats(tornado.web.UIModule):
    def render(self, rule):
        search = {'rules': rule._id, 'finished': {'$ne': None}}
        played_count = self.handler.db.Play.find(search).count()
        unique_players = set()
        play_ids = []
        for p in self.handler.db.Play.collection.find(search):
            for user in p['users']:
                unique_players.add(str(user.id))
            play_ids.append(p['_id'])

#        t0=time.time()
        times = self._get_average_times(rule._id, play_ids=play_ids)
#        t1=time.time()
#        print t1-t0

        options = {
          'played_count': played_count,
          'unique_players': len(unique_players),
          'times': times,
        }
        return self.render_string('rules/rules_stats.html', **options)

    def _get_average_times(self, rule_id, play_ids=None, expires=60 * 60):
        global _times_cache
        try:
            expired, results = _times_cache[rule_id]
            if expired > time.time():
                return results
        except KeyError:
            pass

        if play_ids is None:
            search = {'rules': rule_id, 'finished': {'$ne': None}}
            play_ids = [x['_id'] for x in
                        self.handler.db.Play.collection.find(search)]
        times = defaultdict(list)

        for pq in (self.handler.db.PlayedQuestion.collection
                   .find({'play.$id': {'$in': play_ids},
                          'time': {'$ne': None}},
                         fields=('time','right','answer')
                         )):
            if pq['right']:
                times['right'].append(pq['time'])
            elif pq['answer']:
                times['wrong'].append(pq['time'])

        if times.get('right'):
            times['right'] = sum(times['right']) / len(times['right'])

        if times.get('wrong'):
            times['wrong'] = sum(times['wrong']) / len(times['wrong'])

        _times_cache[rule_id] = (time.time() + expires, times)
        return times


    def _get_average_times_map_reduce(self, rule_id, play_ids=None, expires=60 * 60):
        global _times_cache
        try:
            expired, results = _times_cache[rule_id]
            if expired > time.time():
                return results
        except KeyError:
            pass

        if play_ids is None:
            search = {'rules': rule_id, 'finished': {'$ne': None}}
            play_ids = [x['_id'] for x in
                        self.handler.db.Play.collection.find(search)]

        result = self.handler.db.PlayedQuestion.collection.map_reduce(
          map_, reduce_, 'myoutput',
          finalize=finalize,
          query={'play.$id': {'$in': play_ids},
                 'time': {'$ne': None},
                 #'right': True
                 }
        )
        times = {}
        for reduction in result.find():
            if reduction['_id'] == 'right':
                times['right'] = reduction['value']['avg']
            elif reduction['_id'] == 'wrong':
                times['wrong'] = reduction['value']['avg']
        return times


from bson.code import Code
map_ = Code("""
function() {
  if (this.right)
    emit('right', {total:this.time, count:1});
  if (!this.right && this.answer)
    emit('wrong', {total:this.time, count:1});
}
""")

reduce_ = Code("""
function r( who , values ){
  var n = { total : 0 , count : 0 };
  for ( var i=0; i<values.length; i++ ){
    n.total += values[i].total;
    n.count += values[i].count;
  }
  return n;
}
""")

finalize = Code("""
function f( who , res ){
    res.avg = res.total / res.count;
    return res;
 }
""")
