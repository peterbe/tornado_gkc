from base import BaseModelsTestCase

class ModelsTestCase(BaseModelsTestCase):

    def test_play(self):
        user1 = self.db.User()
        user1.username = u'peter'
        user1.save()

        play = self.db.Play()
        play.users.append(user1)
        play.no_players += 1
        play.no_questions = 10
        play.save()

        self.assertTrue(play.started)
        self.assertTrue(not play.draw)
        self.assertTrue(not play.winner)
