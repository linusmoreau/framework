import random
from toolkit import CustomObject


_days_per_month = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
months = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June", 7: "July", 8: "August",
          9: "September", 10: "October", 11: "November", 12: "December"}


class Date(CustomObject):

    def __init__(self, year=None, month: int = 0, day: int = 0, text=None, form='stnd'):
        if type(month).__name__ != "int":
            raise TypeError("month is type " + type(month).__name__ + ", not int")
        if text is not None:
            if form == 'stnd':
                year, month, day = text.split('-')
            elif form == "mdy":
                month, day, year = text.split()
                day = day.strip(',')
                month = get_month_number(month)
            elif form == "dmy":
                day, month, year = text.split()
                month = get_month_number(month)
            elif form == "ymd":
                year, month, day = text.split()
                month = get_month_number(month)
            year = int(year)
            month = int(month)
            day = int(day)
        self.year = year
        self.month = month
        self.day = day
        if self.month > 12 or self.month < 1 or \
                self.day > get_month_length(self.month, self.year):
            raise ValueError("No date exists with specified attributes.")

    def __repr__(self):
        return str(self.year) + '-' + str(self.month).rjust(2, '0') + '-' + str(self.day).rjust(2, '0')

    def identifier(self):
        return self.__repr__()

    def json_dump(self):
        return self.__repr__()

    def copy(self):
        return Date(self.year, self.month, self.day)

    def change_date(self, dif):
        self.year, self.month, self.day = self.fdif(dif)

    def get_date(self, dif):
        year, month, day = self.fdif(dif)
        return Date(year, month, day)

    def between(self, start, end) -> bool:
        dates = [start, end, self]
        tots = []
        for i in range(len(dates)):
            tots.append(dates[i].year * 10000 + dates[i].month * 100 + dates[i].day)
        if tots[0] <= tots[2] <= tots[1]:
            return True
        else:
            return False

    def day_of_year(self):
        return sum([get_month_length(m, self.year) for m in range(1, self.month)]) + self.day

    def fdif(self, dif):
        year = self.year
        month = self.month
        day = self.day + dif
        while True:
            month_length = get_month_length(month, year)
            year_length = get_year_length(year)
            if day > year_length:
                day -= year_length
                year += 1
            elif day <= -year_length:
                year -= 1
                day += year_length
            elif day > month_length:
                day -= month_length
                month += 1
                if month > 12:
                    year += 1
                    month -= 12
            elif day <= 0:
                month -= 1
                if month < 1:
                    month += 12
                    year -= 1
                day += get_month_length(month, year)
            else:
                break
        return year, month, day

    def numerate(self):
        return self.day + self.month * 100 + self.year * 10000


def get_month_number(month: str):
    month = month[0].upper() + month[1:].lower()
    for num, name in months.items():
        if month == name or month == name[:3]:
            return num
    else:
        return month


def get_month_length(month, year):
    month_length = _days_per_month[month]
    if month == 2 and leap_year(year):
        month_length += 1
    return month_length


def get_year_length(year):
    if leap_year(year):
        return 366
    else:
        return 365


def leap_year(year):
    if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
        return True
    else:
        return False


def age(birthdate: Date, currentdate: Date) -> int:
    years = currentdate.year - birthdate.year
    if currentdate.month < birthdate.month or \
            (currentdate.month == birthdate.month and currentdate.day < birthdate.day):
        years -= 1
    return years


def random_date(year) -> Date:
    month = random.randrange(1, 13)
    day = random.randrange(1, get_month_length(month, year))
    return Date(year, month, day)


def date_dif(idate: Date, fdate: Date) -> int:
    dif = 0
    if idate != fdate:
        fth = sum([get_month_length(m, fdate.year) for m in range(1, fdate.month)]) + fdate.day - 1
        ith = sum([get_month_length(m, idate.year) for m in range(1, idate.month)]) + idate.day - 1
        dif += fth - ith
        if fdate.year > idate.year:
            y1 = idate.year
            y2 = fdate.year
            rel = 0
        else:
            y2 = idate.year
            y1 = fdate.year
            rel = 1
        ydif = 0
        while y1 != y2:
            ydif += get_year_length(y1)
            y1 += 1
        if rel == 0:
            dif += ydif
        else:
            dif -= ydif
        return dif


if __name__ == "__main__":
    date = Date(2020, 3, 1)
    print(date)
    print(date.day_of_year())
