import random

class ComputerClient(object):

    def __init__(self, user_id, user_name='Computer'):
        self.user_id = user_id
        self.user_name = user_name

    def send(self, msg):
        #print "-C->", msg
        pass


def predict_bot_answer(max_time, knowledge):
    """return a dict of 4 keys.

    1. seconds:
        number between 1 and <max_time> seconds for when the bot should send in
        an answer

    2. right:
        if the bot will send the right answer

    3. wrong:
        if the bot will send the wrong answer

    4. alternatives:
        if the bot loads alternatives

    """
    # a third of 6 seconds rounded is 1 which is too low
    assert max_time > 6 #

    def third(t):
        return int(t * 0.333)

    def half(t):
        return int(t * 0.5)

    # "randomly" pick a number of seconds.
    # never make it less than 2 seconds
    if knowledge['right'] >= 0.5:
        sec_range = (2, half(max_time))
    elif knowledge['right'] >= 0.3:
        sec_range = (third(max_time), max_time - 1)
    else:
        sec_range = (2 * third(max_time), max_time)

    # XXX: I'm wondering, if the 'seconds == sec_range[1]' it should perhaps
    # not bother since it's not possible to answer in the last second. Maybe.
    seconds = random.randint(sec_range[0], sec_range[1])

    # lay out all the possible outcomes
    ranges = {}
    prev = 0
    max_ = 0
    keys = ('right', 'wrong', 'alternatives_right', 'alternatives_wrong',)
        #    'too_slow', 'timed_out')
    for key in keys:
        p = max(100 * knowledge[key], 1) # always add 1 percent chance
        ranges[key] = (int(prev), int(prev + p))
        max_ = prev + p
        prev = max_

    ranges[keys[-1]] = (ranges[keys[-1]][0],
                        ranges[keys[-1]][1] + 1)

    #from pprint import pprint
    #pprint(ranges)
    #print "max_", max_

    dice = random.randint(0, int(max_) - 1)
    for key, (x, y) in ranges.items():
        if dice >= x and dice < y:
            lucky_key = key
            break

    if lucky_key in ('right', 'alternatives_right'):
        return dict(seconds=seconds,
                    right=True,
                    alternatives=lucky_key == 'alternatives_right',
                    wrong=False)
    elif lucky_key in ('wrong', 'alternatives_wrong'):
        return dict(seconds=seconds,
                    right=False,
                    alternatives=lucky_key == 'alternatives_wrong',
                    wrong=True)
