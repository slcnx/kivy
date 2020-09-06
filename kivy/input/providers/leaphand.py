'''
Leap Motion - Hand only
=======================

This module provides access to the hand objects generated by the
LeapMotion input provider. The provider generates :class:`MotionEvent` s based
on the hand positions within the Leap Interaction box.

LeapHand vs. LeapFinger Providers
---------------------------------

The `LeapFinger` provider generates fine-grained input based on each of the
fingers tracked by the LeapMotion. Whilst powerful, this provider does not 
generate any useful events as is, and requires the programmer to explicitley
capture these events.

The `LeapHand` provider, however, simulates a more traditional pointing device
in order to generate the traditional `on_touch_down`, `on_touch_move` and 
`on_touch_up` events. It thus aims to be a drop-in alternative for touch
screen and mouse input.

LeapHand Mechanics
------------------

In order to initiate the touch gesture, the :class:`LeapHand` uses the pinch
gesture. A pinch initiates an `on_touch_down` event, and separating the
fingers initiates the `on_touch_up`.

'''

__all__ = ('LeapHandEventProvider', 'LeapHandEvent')

from collections import deque
from kivy.logger import Logger
from kivy.input.provider import MotionEventProvider
from kivy.input.factory import MotionEventFactory
from kivy.input.motionevent import MotionEvent

_LEAP_QUEUE = deque()

Leap = InteractionBox = None


def normalize(value, a, b):
    return (value - a) / float(b - a)


class LeapHandEvent(MotionEvent):

    def depack(self, args):
        super(LeapHandEvent, self).depack(args)
        if args[0] is None:
            return
        self.profile = ('pos', 'pos3d', )
        x, y, z = args
        self.sx = normalize(x, -150, 150)
        self.sy = normalize(y, 40, 460)
        self.sz = normalize(z, -350, 350)
        self.z = z
        self.is_touch = True


class LeapHandEventProvider(MotionEventProvider):

    __handlers__ = {}

    def start(self):
        # Don't import at the start, or the error will be displayed
        # for users who don't have Leap
        global Leap, InteractionBox
        import Leap
        from Leap import InteractionBox

        class LeapMotionListener(Leap.Listener):

            def on_init(self, controller):
                Logger.info('leaphand: Initialized')

            def on_connect(self, controller):
                Logger.info('leaphand: Connected')

            def on_disconnect(self, controller):
                Logger.info('leaphand: Disconnected')

            def on_frame(self, controller):
                frame = controller.frame()
                _LEAP_QUEUE.append(frame)

            def on_exit(self, controller):
                pass

        self.uid = 0
        self.touches = {}
        self.listener = LeapMotionListener()
        self.controller = Leap.Controller(self.listener)

    def update(self, dispatch_fn):
        try:
            while True:
                frame = _LEAP_QUEUE.popleft()
                events = self.process_frame(frame)
                for ev in events:
                    dispatch_fn(*ev)
        except IndexError:
            pass

    def process_frame(self, frame):
        events = []
        touches = self.touches
        available_uid = []
        for hand in frame.hands:
            uid = hand.id
            available_uid.append(uid)
            # position = finger.tip_position  # TODO
            args = (position.x, position.y, position.z)
            if uid not in touches:
                touch = LeapHandEvent(self.device, uid, args)
                events.append(('begin', touch))
                touches[uid] = touch
            else:
                touch = touches[uid]
                touch.move(args)
                events.append(('update', touch))
        for key in list(touches.keys())[:]:
            if key not in available_uid:
                events.append(('end', touches[key]))
                del touches[key]
        return events


# registers
MotionEventFactory.register('leaphand', LeapFingerEventProvider)
