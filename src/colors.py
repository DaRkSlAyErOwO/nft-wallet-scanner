try:
    import colorama
    from colorama import Fore, Style
    colorama.init()
    CYAN = Fore.CYAN
    GREEN = Fore.GREEN
    RED = Fore.RED
    YELLOW = Fore.YELLOW
    MAGENTA = Fore.MAGENTA
    WHITE = Fore.WHITE
    DIM = Style.DIM
    RESET = Style.RESET_ALL
except ImportError:
    CYAN = GREEN = RED = YELLOW = MAGENTA = WHITE = DIM = RESET = ""

def get_status_color(status):
    if status == 'done':
        return GREEN
    return RED

def get_hand_color(hand):
    if hand in ('Diamond', 'Platinum'):
        return MAGENTA
    if hand == 'Gold':
        return YELLOW
    if hand in ('Paper', 'Flipper'):
        return RED
    if hand in ('NonCollector', 'Empty'):
        return RED
    return YELLOW

def get_score_color(score):
    try:
        score = int(score)
        if score >= 70:
            return GREEN
        if score >= 40:
            return YELLOW
        return DIM + WHITE
    except:
        return DIM + WHITE
