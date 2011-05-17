import unittest
from apps.play.battle import Battle, BattleError

class MockClient:
    def __init__(self, user_id, user_name):
        self.user_id = user_id
        self.user_name = user_name

class MockQuestion:
    def __init__(self, text, answer, alternatives, accept, spell_correct):
        self.text = text
        self.answer = answer
        self.alternatives = alternatives
        self.accept = accept
        self.spell_correct = spell_correct

class BattleTestCase(unittest.TestCase):

    def test_participants(self):
        battle = Battle(10, min_no_people=2, max_no_people=2)
        client = MockClient('123', 'peter')
        battle.add_participant(client)

        # can't add any junk
        self.assertRaises(AttributeError, battle.add_participant, object())
        junk_client = MockClient(0, 0)
        self.assertRaises(AssertionError, battle.add_participant, junk_client)

        #self.assertTrue(battle.participants)
        self.assertFalse(battle.ready_to_play())
        self.assertTrue(battle.is_open())

        client2 = MockClient('222', 'chris')
        battle.add_participant(client2)
        self.assertTrue(battle.ready_to_play())
        self.assertFalse(battle.is_open())

        client3 = MockClient('333', 'frick')
        self.assertRaises(BattleError, battle.add_participant, client3)

        battle.remove_participant(client)
        self.assertFalse(battle.ready_to_play())
        self.assertFalse(battle.is_open())

    def test_check_answer_without_spell_correct(self):
        question = MockQuestion("WHy?", "right",
                                ['one','two','three','four'],
                                ['correcT'],
                                False)
        battle = Battle(10)
        battle.current_question = question
        self.assertTrue(battle.check_answer('RIGHT'))
        self.assertTrue(battle.check_answer('RIght '))
        self.assertTrue(battle.check_answer(' CORREct'))
        self.assertFalse(battle.check_answer('rght'))
        self.assertFalse(battle.check_answer('rigght'))

    def test_check_answer_with_spell_correct(self):
        question = MockQuestion("WHy?", "right",
                                ['one','two','three','four'],
                                ['correcT'],
                                True)
        battle = Battle(10)
        battle.current_question = question
        self.assertTrue(battle.check_answer('RIGHT'))
        self.assertTrue(battle.check_answer('RIght '))
        self.assertTrue(battle.check_answer(' CORREct'))
        self.assertTrue(battle.check_answer('rght'))
        self.assertTrue(battle.check_answer('rigght'))
        self.assertTrue(battle.check_answer(' CORRREct'))
