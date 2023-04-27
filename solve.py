from collections import Counter, defaultdict
from multiprocessing import Pool, freeze_support
from itertools import repeat
from tqdm.contrib.concurrent import process_map
import string

DEBUG = True


def dbg(s):
    if DEBUG:
        print(s)


class Wordlist:
    def __init__(self, path='wordle-answers', unique_letters=False):
        with open(path) as dictionary:
            self.words = set()
            for w in [_.strip().lower() for _ in dictionary.readlines()]:
                if len(w) != 5:
                    continue  # Only 5 letters
                if unique_letters and len(set(w)) != 5:
                    continue  # If unique_letters, there's 5 unique letters
                if sum([w.count(c) for c in string.ascii_lowercase]) != 5:
                    continue  # Only 5 alphabet characters allowed
                self.words.add(w)
            dbg(f"Loaded {len(self.words)} words")


class Game:
    def __init__(self, answer):
        self.answer = answer
        self.solved = False
        self.prior = []

    def guess(self, guess):
        # We could validate that the guess is a legal word, but let's pretend we trust you - for now.
        dbg(f"You've guessed '{guess}'")
        self.prior.append(guess)
        bad_letters, known_letter_pos, good_letters_possible_places = set(), {}, {}

        for idx, c in enumerate(guess):
            if c in self.answer:
                if self.answer[idx] == c:
                    known_letter_pos[1 + idx] = c
                else:
                    if c in good_letters_possible_places:
                        good_letters_possible_places[c].remove(1 + idx)
                    else:
                        good_letters_possible_places[c] = [i for i in range(1, 6) if i != 1 + idx]
            else:
                bad_letters.add(c)

        if len(known_letter_pos) == 5:
            self.solved = True

        return {
            'good_letters_possible_places': dict(good_letters_possible_places),
            'bad_letters': list(bad_letters),
            'known_letter_pos': known_letter_pos
        }


class GameCache:
    def __init__(self, wordlist=None):
        self.wordlist = wordlist if wordlist else Wordlist()
        self.possible_words = wordlist.words
        self.good_letters_no_pos = set()
        self.bad_letters = set()
        self.known_letter_pos = dict()

    def refine(self, bad_letters=None, known_letter_pos=None, good_letters_possible_places=None):
        if bad_letters:  # We know these letters are definitely not in the solution
            for c in bad_letters:
                self.bad_letters.add(c)
            self.possible_words = [w for w in self.possible_words if all([c not in bad_letters for c in w])]

        if known_letter_pos:  # We know that this letter is definitely in a specific spot
            for c, pos in known_letter_pos.items():
                self.known_letter_pos[pos] = c
            self.possible_words = [w for w in self.possible_words if all([w[pos - 1] == c for
                                                                          (pos, c) in known_letter_pos.items()])]

        if good_letters_possible_places:  # This letter is somewhere in the solution, but we're not exactly sure where.
            new_words = set()
            for w in self.possible_words:
                keep = True
                for c, poses in good_letters_possible_places.items():
                    if c not in w:
                        keep = False
                        break
                if keep:
                    for c, poses in good_letters_possible_places.items():
                        if not keep:
                            break
                        for pos in [i for i in range(1, 6) if i not in poses]:
                            if w[pos - 1] == c:
                                keep = False
                                break
                if keep:
                    new_words.add(w)

            self.possible_words = new_words

        dbg(f"Now {len(self.possible_words)} possible words")

    def suggest(self, guess_number):
        if guess_number == 0:
            return 'raise'

        f = ''
        for w in self.possible_words:
            _ = w
            for c in self.good_letters_no_pos:
                _ = _.replace(c, "_")
            for c, pos in self.known_letter_pos.items():
                _ = "".join([c.upper() if idx == pos - 1 else let for idx, let in enumerate(_)])
            f += _
            dbg(_)
        co = Counter(f)
        del co['_']
        del co['*']
        print(co)

        if guess_number == 1:
            return 'split'


class GuessTracker:
    def __init__(self, word):
        self.word = word
        self.min = None
        self.max = None
        self.total = 0
        self.count = 0

    def add_result(self, remaining_words):
        self.min = remaining_words if self.min is None else min(self.min, remaining_words)
        self.max = remaining_words if self.max is None else max(self.max, remaining_words)
        self.total += remaining_words
        self.count += 1

    def avg(self):
        return int(1000 * self.total / self.count) / 1000

    def __repr__(self):
        return f"{self.word.upper()}: {self.avg()} (min: {self.min}, max: {self.max})"




def benchmark_guess(guess, answers=Wordlist('wordle-answers')):
    tracker = GuessTracker(guess)
    for ans in answers.words:
        game = Game(ans)
        gc = GameCache(answers)  # Only answers are valid answers - doh.

        hints = game.guess(guess)
        dbg(f"Returned hints: {hints}")
        gc.refine(**hints)

        tracker.add_result(len(gc.possible_words))
    return tracker


def calculate_best_worst_first_guess():
    first = ['roate', 'raise', 'raile', 'soare', 'arise', 'irate', 'orate', 'ariel', 'arose', 'raine', 'artel', 'taler', 'ratel', 'aesir', 'arles', 'realo', 'alter', 'saner', 'later', 'snare', 'oater', 'salet', 'taser', 'stare', 'tares', 'slate', 'alert', 'reais', 'lares', 'reast']

    guess_tracker = process_map(benchmark_guess, first, max_workers=6, chunksize=1)

    print("Best:")
    for t in sorted(guess_tracker, key=lambda _t: _t.avg())[:30]:
        print(t)

    print("")
    print("Worst")
    for t in sorted(guess_tracker, key=lambda _t: _t.avg())[-30:]:
        print(t)


if __name__ == '__main__':
    #calculate_best_worst_first_guess()

    w_list = Wordlist('wordle-list')
    answers = Wordlist('wordle-answers')
    #answers = Wordlist('lordle')
    
    ll = len(w_list.words)
    gc = GameCache(answers)

    gc.refine(**{'good_letters_possible_places': {'o': [1,3,4,5]}, 'bad_letters': ['m', 'v', 'i', 'e'], 'known_letter_pos': {}})
    gc.refine(**{'good_letters_possible_places': {'n': [1,2,4,5], 's': [1,2,3,4]}, 'bad_letters': ['l', 'a', 'd'], 'known_letter_pos': {}})
    gc.refine(**{'good_letters_possible_places': {'t': [1,2,3,5]}, 'bad_letters': ['w', 'r', 'h'], 'known_letter_pos': {}})
    gc.suggest(10)


    for w in gc.possible_words:
        print(w)
