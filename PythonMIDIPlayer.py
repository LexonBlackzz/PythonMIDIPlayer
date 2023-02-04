'''
midiplay2 rev1 - MIDI player written in Python 3.6 for Windows
Copyright (C) 2021 Sono (https://github.com/SonoSooS)
All Rights Reserved
'''

import sys
import struct
import io
import ctypes

import threading
from random import randint

import sdl2
import sdl2.ext

try:
    from sdl2 import (SDL_QUIT, SDL_MOUSEBUTTONDOWN, SDL_Color,
                      SDL_BlitSurface, SDL_GetPerformanceFrequency, SDL_GetError,
                      SDL_GetPerformanceCounter, SDL_SetWindowTitle)
    import sdl2.ext as sdl2ext
except ImportError:
    import traceback
    traceback.print_exc()
    sys.exit(1)

screen_height = 480*2
noteWidth = 10
screen_width = 128*noteWidth
sdl2ext.init()
window = sdl2ext.Window("Python MIDI Player",
                        size=(screen_width, screen_height))
window.show()

surface = window.get_surface()


# PFA colors as RGB tuples (you can replace these colors with anything.)
colors = [(51, 102, 255), (255, 126, 51), (51, 255, 102), (255, 51, 129), (51, 255, 255), (228, 51, 255), (153, 255, 51), (75, 51, 255),
          (255, 204, 51), (51, 180, 255), (255, 51, 51), (51, 255, 177), (255, 51, 204), (78, 255, 51), (153, 51, 255), (231, 255, 51)]

# Set up the note falling speed (in pixels per frame)
falling_speed = 2000

# Constants
TRACK_DATA = 0
TRACK_TICK = 1
TRACK_OFFS = 2
TRACK_LEN = 3
TRACK_MSG = 4
TRACK_TMP = 5
TRACK_LMSGLEN = 6
TRACK_LMSG = 7

PLAYER_TICK = 0
PLAYER_MULTI = 1
PLAYER_BPM = 2
PLAYER_DELTATICK = 3

SLEEP_LASTTIME = 0
SLEEP_MAXDRIFT = 1
SLEEP_DELTA = 2
SLEEP_OLD = 3
SLEEP_TMP = 4

# Oneliner idioms

iter_empty = (None for _ in {})
iter_stop = (lambda: next(iter_empty))

complete_iterate = (lambda x: sum(0 for _ in x))

reduce_inner_cb_whiledo = (lambda x, y, z: x.__setitem__(
    0, z(x[0])) if y(x[0]) else x.__setitem__(1, 0))
reduce_inner_cb_dowhile = (lambda x, y, z: x.__setitem__(
    0, z(x[0])) or (y(x[0]) or x.__setitem__(1, 0)))

iterjunk = None if sys.hexversion < 0x3070000 else __import__(
    'itertools').takewhile

reduce_inner = (lambda x, y, z, cb: x[0] if not sum(0 for __ in ((cb(x, y, z) if x[1] else iter_stop()) for _ in iter(int, 1))) else None) if not iterjunk else (
    lambda x, y, z, cb: sum(0 for _ in iterjunk(lambda w: (x[1] and cb(x, y, z)) or x[1], iter(int, 1))) or x[0])

while_do = (lambda x, y, z: reduce_inner(
    [x, 1], y, z, reduce_inner_cb_whiledo))
do_while = (lambda x, z, y: reduce_inner(
    [x, 1], y, z, reduce_inner_cb_dowhile))


# Track class definition C-style

track_decode_varlen = (lambda track:
                       (
                           do_while([track, 0, 0],
                                    lambda x:
                                    (
                               x.__setitem__(
                                   2, x[0][TRACK_DATA][x[0][TRACK_OFFS]])
                               or x.__setitem__(1, (x[1] << 7) + (x[2] & 0x7F))
                               or x
                           ),
                               lambda x:
                               (
                               x[0].__setitem__(
                                   TRACK_OFFS, x[0][TRACK_OFFS] + 1)
                               or x[2] >= 0x80
                           )
                           )[1]
                       ))

track_update_tick = (lambda track:
                     (
                         track.__setitem__(
                             TRACK_TICK, track[TRACK_TICK] + track_decode_varlen(track))
                     ))

track_update_cmd = (lambda track:
                    (
                        track.__setitem__(
                            TRACK_TMP, track[TRACK_DATA][track[TRACK_OFFS]])
                        or
                        (
                            (
                                track.__setitem__(
                                    TRACK_OFFS, track[TRACK_OFFS] + 1)
                                or track.__setitem__(TRACK_MSG, track[TRACK_TMP])
                            )
                            if track[TRACK_TMP] >= 0x80
                            else
                            (
                                track.__setitem__(
                                    TRACK_MSG, track[TRACK_MSG] & 0xFF)
                            )
                        )
                    ))

track_update_msg = (lambda track:
                    (
                        (
                            (
                                track.__setitem__(
                                    TRACK_TMP, track[TRACK_DATA][track[TRACK_OFFS]] << 8)
                                or track.__setitem__(TRACK_TMP, track[TRACK_TMP] | (track[TRACK_DATA][track[TRACK_OFFS] + 1] << 16))
                                or track.  __setitem__(TRACK_OFFS, track[TRACK_OFFS] + 2)
                            )
                            if track[TRACK_MSG] < 0xC0
                            else
                            (
                                (
                                    (
                                        track.__setitem__(
                                            TRACK_TMP, track[TRACK_DATA][track[TRACK_OFFS]] << 8)
                                        or track.__setitem__(TRACK_OFFS, track[TRACK_OFFS] + 1)
                                    )
                                    if track[TRACK_MSG] < 0xE0
                                    else
                                    (
                                        track.__setitem__(
                                            TRACK_TMP, track[TRACK_DATA][track[TRACK_OFFS]] << 8)
                                        or track.__setitem__(TRACK_TMP, track[TRACK_TMP] | (track[TRACK_DATA][track[TRACK_OFFS] + 1] << 16))
                                        or track.__setitem__(TRACK_OFFS, track[TRACK_OFFS] + 2)
                                    )
                                )
                                if track[TRACK_MSG] < 0xF0
                                else
                                (
                                    (
                                        track.__setitem__(
                                            TRACK_TMP, track[TRACK_DATA][track[TRACK_OFFS]] << 8)
                                        or track.__setitem__(TRACK_OFFS, track[TRACK_OFFS] + 1)
                                        or track.__setitem__(TRACK_LMSGLEN, track_decode_varlen(track))
                                        or track.__setitem__(TRACK_LMSG, track[TRACK_DATA][track[TRACK_OFFS]: track[TRACK_OFFS] + track[TRACK_LMSGLEN]])
                                        or track.__setitem__(TRACK_OFFS, track[TRACK_OFFS] + track[TRACK_LMSGLEN])
                                    )
                                    if track[TRACK_MSG] == 0xFF
                                    else
                                    (
                                        (
                                            track.__setitem__(TRACK_TMP, 0)
                                            or track.__setitem__(TRACK_LMSGLEN, track_decode_varlen(track))
                                            or track.__setitem__(TRACK_LMSG, track[TRACK_DATA][track[TRACK_OFFS]: track[TRACK_OFFS] + track[TRACK_LMSGLEN]])
                                            or track.__setitem__(TRACK_OFFS, track[TRACK_OFFS] + track[TRACK_LMSGLEN])
                                        )
                                        if track[TRACK_MSG] == 0xF0
                                        else iter_stop()
                                    )
                                )
                            )
                        )
                        or track.__setitem__(TRACK_MSG, track[TRACK_MSG] | track[TRACK_TMP])
                    ))

def seton(a, b):
    notes[(a,b)] = True

def setoff(a,b):
    try:
        del notes[(a,b)]
    except Exception:
        pass

track_execute_cmd = (lambda track:
                     (
                         (KShortMsg(track[TRACK_MSG]), seton((track[TRACK_MSG]>>8)&0xFF,track[TRACK_MSG]&0x0F) if (track[TRACK_MSG] & 0xF0 == 0x90)
                          else (), setoff(track[TRACK_MSG]>>8&0xFF,track[TRACK_MSG]& 0x0F) if (track[TRACK_MSG] & 0xF0 == 0x80) else ())[0]
                         if ((track[TRACK_MSG] & 0xFF) < 0xF0)
                         else
                         (
                             (
                                 track.__setitem__(TRACK_TMP, (track[TRACK_MSG] >> 8) & 0xFF) or
                                 (
                                     (
                                         player.__setitem__(PLAYER_BPM, (track[TRACK_LMSG][0] << 16) | (
                                             track[TRACK_LMSG][1] << 8) | (track[TRACK_LMSG][2]))
                                         or player.__setitem__(PLAYER_MULTI, (player[PLAYER_BPM] * 10 / timediv) or 1)
                                     )
                                     if track[TRACK_TMP] == 0x51
                                     else
                                     (
                                         track.__setitem__(TRACK_DATA, 0)
                                     )
                                     if track[TRACK_TMP] == 0x2F
                                     else
                                     (
                                         print("Meta{}: {}".format(
                                             hex(track[TRACK_TMP]), track[TRACK_LMSG])) or None
                                     )
                                     if track[TRACK_TMP] < 0x10
                                     else None
                                 )
                             )
                             if (track[TRACK_MSG] & 0xFF) == 0xFF else
                             (
                                 (
                                     # TODO: longmsg
                                     print("TODO longmsg")
                                 )
                                 if (track[TRACK_MSG] & 0xFF) == 0xF0
                                 else iter_stop()
                             )
                         )
                     ))

player_sleep = (lambda:
                (
                    NtQuerySystemTime(ticker_ptr)
                    or sleep.__setitem__(SLEEP_TMP, ticker.value - sleep[SLEEP_LASTTIME])
                    or sleep.__setitem__(SLEEP_LASTTIME, ticker.value)
                    or sleep.__setitem__(SLEEP_TMP, sleep[SLEEP_TMP] - sleep[SLEEP_OLD])
                    or sleep.__setitem__(SLEEP_OLD, player[PLAYER_DELTATICK] * player[PLAYER_MULTI])
                    or sleep.__setitem__(SLEEP_DELTA, sleep[SLEEP_DELTA] + sleep[SLEEP_TMP])
                    or sleep.__setitem__(SLEEP_TMP, sleep[SLEEP_OLD] - sleep[SLEEP_DELTA] if sleep[SLEEP_DELTA] > 0 else sleep[SLEEP_OLD])
                    or
                    (
                        sleep.__setitem__(SLEEP_DELTA, min(
                            sleep[SLEEP_DELTA], sleep[SLEEP_MAXDRIFT]))
                        if sleep[SLEEP_TMP] <= 0
                        else
                        (
                            sleepval.__setattr__(
                                'value', -int(sleep[SLEEP_TMP]))
                            or ((NtDelayExecution(ctypes.c_int(1), sleepval_ptr) or 1) and None)
                        )
                    )
                ))

# Real code begins from here

ks = ctypes.WinDLL("C:\\Windows\\System32\\OmniMIDI.dll")

sys.exit(1) if not ks.IsKDMAPIAvailable(
) or not ks.InitializeKDMAPIStream() else None

KShortMsg = ks.SendDirectData
KShortMsg.restype = None


NtDelayExecution = ctypes.windll.ntdll.NtDelayExecution
NtQuerySystemTime = ctypes.windll.ntdll.NtQuerySystemTime
NtQuerySystemTime.restype = None

sleep = [0, 100000, 0, 0, 0]

ticker = ctypes.c_ulonglong(0)
ticker_ptr = ctypes.byref(ticker)
sleepval = ctypes.c_longlong(-1)
sleepval_ptr = ctypes.byref(sleepval)

fh = io.open(sys.argv[1], "rb")
fh.__enter__()

(fh.__exit__(), print("Not MThd"), sys.exit(1)) if fh.read(4) != b'MThd' else None
(fh.__exit__(), print("Invalid header length"), sys.exit(
    1)) if fh.read(4) != b'\x00\x00\x00\x06' else None
(fh.__exit__(), print("Corrupted file"),
 sys.exit(1)) if fh.read(1)[0] else None
(fh.__exit__(), print("Unsupported MIDI version"),
 sys.exit(1)) if fh.read(1)[0] > 1 else None

trackcount, timediv = struct.unpack('>HH', fh.read(4))

(fh.__exit__(), print("SMTPE timing not supported"),
 sys.exit(1)) if timediv >= 0x8000 else None

print("Loading %i tracks" % trackcount)

player = [0, (5000000 / timediv) or 1, 500000, 0]

running = True

tracks = list(
    (
        [t, 0, 0, len(t), 0, 0, 0, 0] for t in
        (
            None if fh.read(4) != b'MTrk' else
            (
                fh.read(struct.unpack('>I', fh.read(4))[0])
            )
            for trackid in range(0, trackcount)
        )
    ))

fh.__exit__()

complete_iterate(track_update_tick(track) for track in tracks)

NtQuerySystemTime(ticker_ptr)
sleep[SLEEP_LASTTIME] = ticker.value


def draw_rects(surface, width, height):
    # Fill the whole surface with a black color. You can also change this to any color
    sdl2ext.fill(surface, 0)
    for k in range(15):
        # Create a set of four random points for the edges of the rectangle.
        x, y = randint(0, width), randint(0, height)
        w, h = randint(1, width // 2), randint(1, height // 2)
        # Create a random color.
        color = sdl2ext.Color(randint(0, 255),
                              randint(0, 255),
                              randint(0, 255))
        # Draw the filled rect with the specified color on the surface.
        # We also could create a set of points to be passed to the function
        # in the form
        #
        # fill(surface, color, ((x1, y1, x2, y2), (x3, y3, x4, y4), ...))
        #                        ^^^^^^^^^^^^^^    ^^^^^^^^^^^^^^
        #                          first rect        second rect
        sdl2ext.fill(surface, color, (x, y, w, h))


notes = dict()

running = True

def play():
    do_while(tracks,
             lambda tracks:
             (
                 complete_iterate
                 (
                     (
                         while_do
                         (
                             track,
                             lambda track: (
                                 track and track[TRACK_TICK] <= player[PLAYER_TICK]),
                             lambda track:
                             (
                                 track_update_cmd(track)
                                 or track_update_msg(track)
                                 or track_execute_cmd(track)
                                 or (track[TRACK_DATA] and (track_update_tick(track) or track))
                             )
                         )
                     )
                     if track[TRACK_TICK] <= player[PLAYER_TICK] else None
                     for track in tracks
                 )
                 or
                 (
                     player.__setitem__(PLAYER_DELTATICK, min(
                         track[TRACK_TICK] for track in tracks) - player[PLAYER_TICK])
                     or player.__setitem__(PLAYER_TICK, player[PLAYER_TICK] + player[PLAYER_DELTATICK])
                     or player_sleep()
                 )
                 or
                 (
                     tracks if not sum(0 if track[TRACK_DATA] else 1 for track in tracks)
                     else list(track for track in tracks if track[TRACK_DATA])
                 )
             ),
             lambda tracks:
             (
                 len(tracks) if running else 0
             )
             )

rthread = threading.Thread(target=play)
rthread.start()

while running:
    events = sdl2ext.get_events()
    for event in events:
        if event.type == SDL_QUIT:
            running = False
            break
    if running:
        #draw_rects(surface, 800,600)
        sdl2.ext.fill(surface, 0, (0,0,screen_width, 1))
        for note_key, note_properties in notes.copy().items():
            color = sdl2.ext.Color(*colors[note_key[1] % 16])
            rect = sdl2.rect.SDL_Rect(
                note_key[0]*noteWidth, 0, noteWidth, 1)
            sdl2.ext.fill(surface, color, rect)
        sdl2.SDL_BlitSurface(surface, None, surface, sdl2.rect.SDL_Rect(0,1, surface.w, surface.h))
        window.refresh()
sdl2.ext.quit()