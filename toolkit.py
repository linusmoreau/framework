import random
from typing import Dict, List, Tuple


def round_up(num):
    return int(num) + (int(num) != num)


def largest_in_dictionary(d):
    keys = list(d)
    biggest = None
    thics = []
    for key in keys:
        if biggest is None:
            thics.append(key)
            biggest = key
        elif d[key] > d[biggest]:
            biggest = key
            thics = [biggest]
        elif d[key] == d[biggest]:
            thics.append(key)
    if len(thics) > 1:
        biggest = random.choice(thics)
    return biggest


def capitalize(string):
    string = str(string).lower()
    if 97 <= ord(string[0]) <= 122:
        string = chr(ord(string[0]) - 32) + string[1:]
    return string


def entitle(title):
    syncategorematics = {'a', 'an', 'the', 'for', 'and', 'nor', 'but', 'or', 'yet', 'so', 'as', 'at', 'by', 'in', 'of',
                         'on', 'per', 'to', 'with', 'into'}
    title = str(title)
    title = title.replace('_', ' ')
    words = title.split()
    title = capitalize(words.pop(0))
    for word in words:
        title += ' '
        if word.lower() not in syncategorematics:
            title += capitalize(word)
        else:
            title += word.lower()
    return title


def translate_bool_string(string, default=None):
    if string in ["true", 't']:
        out = True
    elif string in ["false", 'f']:
        out = False
    elif string in ["default", 'd']:
        out = default
    else:
        out = None
    return out


def rolling_average(dat: Dict[float, List[float]], breadth: float):
    ndat = {}
    relv: List[Tuple] = []
    for x in sorted(list(dat.keys())):
        for y in dat[x]:
            relv.append((x, y))
        cutoff: int = 0
        for i, point in enumerate(relv):
            if x - point[0] <= breadth:
                cutoff = i
                break
        relv = relv[cutoff:]
        ndat[x] = sum([p[1] for p in relv]) / len(relv)
    return ndat


def central_rolling_average(dat: Dict[float, List[float]], breadth: float):
    ndat = {}
    relv: List[Tuple] = []
    in_ord = sorted(list(dat.keys()))
    mini = in_ord[0]
    first = True
    for x in in_ord:
        for y in dat[x]:
            relv.append((x, y))
        cutoff: int = 0
        for i, point in enumerate(relv):
            if x - point[0] <= breadth:
                cutoff = i
                break
        relv = relv[cutoff:]
        if x >= mini + breadth / 2:
            if first:
                ndat[mini] = sum([p[1] for p in relv]) / len(relv)
                first = False
            else:
                ndat[x - breadth / 2] = sum([p[1] for p in relv]) / len(relv)
    maxi = relv[-1][0]
    in_ord = in_ord[in_ord.index(relv[0][0]):]
    for j, x in enumerate(in_ord):
        cutoff: int = 0
        for i, point in enumerate(relv):
            if point[0] != x:
                cutoff = i
                break
        relv = relv[cutoff:]
        if j + 1 < len(in_ord) and in_ord[j + 1] + breadth / 2 > maxi:
            ndat[maxi] = sum([p[1] for p in relv]) / len(relv)
            break
        else:
            ndat[x + breadth / 2] = sum([p[1] for p in relv]) / len(relv)
    return ndat


def variable_weight(disp, breadth, loc: float = 3):
    w = (1 - (abs(disp) / breadth) ** 2) ** loc
    if w < 0:
        return 0
    else:
        return w


def cube_weight(disp, breadth):
    w = (1 - (abs(disp) / breadth) ** 3) ** 3
    if w < 0:
        return 0
    else:
        return w


def rolling_averages(dat: Dict[str, Dict[float, List[float]]], breadth: float, central: bool = False) \
        -> Dict[str, Dict[float, List[float]]]:
    ndat = {}
    for line, points in dat.items():
        if central:
            npoints = central_rolling_average(points, breadth)
        else:
            npoints = rolling_average(points, breadth)
        ndat[line] = npoints
    return ndat


def weighted_average(dat: Dict[float, List[float]], breadth: float, res: int, loc=False, start=None, end=None,
                     limit=None, line_end=None):
    ratio = 2
    ndat = {}
    relv: List[int] = []

    upcome = sorted(filter(lambda k: len(dat[k]) > 0, list(dat.keys())))
    disc = []
    if start is not None and upcome[0] - breadth / ratio <= start:
        mini = start
    else:
        mini = upcome[0]
    if limit is not None and upcome[-1] + breadth / ratio >= limit and not (end is not None and end < limit):
        maxi = limit
    elif end is not None and upcome[-1] + breadth / ratio >= end:
        maxi = end
    elif limit is None and line_end is not None and upcome[-1] + breadth / ratio >= line_end:
        maxi = line_end
    else:
        maxi = upcome[-1]
    place = mini
    step = (upcome[-1] - upcome[0]) / res
    while True:
        if place > maxi:
            place = maxi
        cutoff: int = -1
        for j, x in enumerate(upcome):
            if x >= place + breadth:
                cutoff = j
                break
        if cutoff == -1:
            relv.extend(upcome)
            upcome = []
        else:
            relv.extend(upcome[:cutoff])
            upcome = upcome[cutoff:]

        cutoff = -1
        for j, x in enumerate(relv):
            if x >= place - breadth:
                cutoff = j
                break
        if cutoff != -1:
            disc.extend(relv[:cutoff])
            relv = relv[cutoff:]
        shown = relv.copy()
        spread = breadth
        try:
            if loc:
                locnum = sum([cube_weight(x - place, spread) for x in shown])
                if locnum < 3:
                    locnum = 3
                ndat[place] = (sum([sum(dat[x]) * variable_weight(x - place, spread, locnum) for x in shown]) /
                               sum([len(dat[x]) * variable_weight(x - place, spread, locnum) for x in shown]))
            else:
                ndat[place] = (sum([sum(dat[x]) * cube_weight(x - place, spread) for x in shown]) /
                               sum([len(dat[x]) * cube_weight(x - place, spread) for x in shown]))
        except ZeroDivisionError:
            pass
        if place == maxi:
            break
        else:
            place += step
    return ndat


def weighted_averages(dat: Dict[str, Dict[float, List[float]]], breadth: int, resratio, loc=False,
                      start=None, end=None, limit=None) \
        -> Dict[str, Dict[float, List[float]]]:
    # Breadth is the x-distance considered in either direction
    ndat = {}
    line_end = max([max(d) for d in dat.values()])
    for line, points in dat.items():
        inres = (max(points) - min(points)) // resratio
        if inres == 0:
            inres = 1
        elif inres < 50:
            inres = 50
        ndat[line] = weighted_average(points, breadth, inres, loc, start=start, end=end, limit=limit, line_end=line_end)
    return ndat


def geothmetic_meandian(seq):
    def arithmetic_mean(seq):
        return sum(seq) / len(seq)

    def geometric_mean(seq):
        tot = None
        for t in seq:
            if tot is None:
                tot = t
            else:
                tot *= t
        return tot ** (1 / len(seq))

    def median(seq):
        seq = sorted(seq)
        if len(seq) % 2 == 0:
            return (seq[(len(seq) + 1) // 2 - 1] + seq[(len(seq) + 1) // 2]) / 2
        else:
            return seq[(len(seq) + 1) // 2 - 1]

    if len(seq) == 3 and abs(seq[0] - seq[1]) + abs(seq[0] - seq[2]) + abs(seq[1] - seq[2]) < 0.001:
        return round(median(seq), 3)
    else:
        inter = (arithmetic_mean(seq), geometric_mean(seq), median(seq))
        # print(inter)
        return geothmetic_meandian(inter)


class CustomObject:
    def json_dump(self):
        def deep_identifier(d):
            if isinstance(d, Dict):
                for k, a in d.items():
                    if isinstance(a, (Dict, List)):
                        d[k] = deep_identifier(a)
                    elif isinstance(a, CustomObject):
                        d[k] = a.identifier()
            elif isinstance(d, List):
                for i, a in enumerate(d):
                    if isinstance(a, (Dict, List)):
                        d[i] = deep_identifier(a)
                    elif isinstance(a, CustomObject):
                        d[i] = a.identifier()
            return d

        attr = self.__dict__.copy()
        attr = deep_identifier(attr)
        attr["type"] = type(self).__name__
        return attr

    def identifier(self):
        raise ValueError("No identifier")


def highest_averages_method(votes: Dict[str, float], num: int, mult=1, bar=0) -> Dict[str, int]:
    # D'Hondt: mult=1, Sainte-Lague: mult=2
    seats = {p: 0 for p in votes.keys()}
    for i in range(num):
        quotients = {votes[p] / (mult * seats[p] + 1 + (bar if seats[p] == 0 else 0)): p for p in votes.keys()}
        winner = quotients[max(quotients)]
        seats[winner] += 1
    return seats


def huntingon_hill(votes: Dict[str, float], num: int):
    seats = {p: 1 for p in votes.keys()}
    for i in range(num - len(seats)):
        quotients = {votes[p] / (seats[p] * (seats[p] + 1)) ** 0.5: p for p in votes.keys()}
        winner = quotients[max(quotients)]
        seats[winner] += 1
    return seats


def largest_remainder_method(votes: Dict[str, float], num: int):
    quota = sum(votes.values()) / num
    seats = {}
    remains = {}
    allocated = 0
    for p in votes:
        quotient = votes[p] / quota
        auto = int(quotient)
        remain = quotient - auto
        seats[p] = auto
        allocated += auto
        remains[remain] = p
    for a in range(num - allocated):
        p = remains.pop(max(remains))
        seats[p] += 1
    return seats


def least_prime_factor(num: int):
    for i in range(2, num + 1):
        if num % i == 0:
            return i
    else:
        raise ValueError


if __name__ == '__main__':
    votes = {'S': 924_940, 'DPP': 741_746, 'V': 685_188, 'RG': 274_463, 'LA': 265_129, 'A': 168_788,
             'SL': 161_009, 'SF': 147_578, 'C': 118_003}
    print(largest_remainder_method(votes, 175))
