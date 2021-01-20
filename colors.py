def wrapped(textstyle):
    return lambda text: textstyle + text + RESET


def sparkle(style1, style2):
    def sparkling(text):
        nt = []
        for i in range(len(text)):
            if i % 2 == 0:
                nt += [style1, text[i]]
            else:
                nt += [style2, text[i]]
        return ''.join(nt) + RESET

    return sparkling

def fore(color):
    return '\033[38;5;%dm' % color

def forebright(color):
    return '\033[38;5;%d;1m' % color

def foredim(color):
    return '\033[38;5;%d;2m' % color


RESET = '\033[0m'

LOWEST = wrapped(forebright(21))
LOW = wrapped(forebright(33))
MIDLOW = wrapped(forebright(159))
MID = wrapped(forebright(154))
MIDHIGH = wrapped(forebright(226))
HIGH = wrapped(forebright(196))
HIGHEST = sparkle(forebright(196), forebright(227))

DISTANT = wrapped(fore(62))
LATER = wrapped(fore(122))
SOON = wrapped(fore(192))
IMPENDING = wrapped(fore(201))
OVERDUE = sparkle(fore(201), fore(213))

OPEN = wrapped(fore(47))
WORKING = sparkle(fore(50), fore(159))
DONE = wrapped(fore(243))
BLOCKED = wrapped(fore(124))

NOTE = wrapped(foredim(178))

PRIORITY_DONE = wrapped(forebright(243))

if __name__ == '__main__':
    teststr = f"""
{LOWEST("LOWEST")}
{LOW("LOW")}
{MIDLOW("MIDLOW")}
{MID("MID")}
{MIDHIGH("MIDHIGH")}
{HIGH("HIGH")}
{HIGHEST("HIGHEST")}

{DISTANT("DISTANT")}
{LATER("LATER")}
{SOON("SOON")}
{IMPENDING("IMPENDING")}
{OVERDUE("OVERDUE")}

{OPEN("OPEN")}
{WORKING("WORKING")}
{DONE("DONE")}
{BLOCKED("BLOCKED")}

{NOTE("NOTE")}
"""
    print(teststr)

