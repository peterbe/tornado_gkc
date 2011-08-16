import time
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
            for id in p['users']:
                unique_players.add(id)
            play_ids.append(p['_id'])

        times = self._get_average_times(rule._id)

        options = {
          'played_count': played_count,
          'unique_players': len(unique_players),
          'times': times,
        }
        return self.render_string('rules/rules_stats.html', **options)

    def _get_average_times(self, rule_id, expires=60 * 60):
        global _times_cache
        try:
            expired, results = _times_cache[rule_id]
            if expired > time.time():
                return results
        except KeyError:
            pass

        search = {'rules': rule_id, 'finished': {'$ne': None}}
        play_ids = [x['_id'] for x in
                    self.handler.db.Play.collection.find(search)]

        times = defaultdict(list)
        for pq in (self.handler.db.PlayedQuestion.collection
                   .find({'play.$id': {'$in': play_ids}})):
            if pq['time'] is not None:
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
