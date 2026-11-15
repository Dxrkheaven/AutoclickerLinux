import math
import select
import threading
import time

from evdev import InputDevice, UInput, UInputError, ecodes as e, list_devices

HOTKEY = e.KEY_F2
BUTTONS = {"left": e.BTN_LEFT, "right": e.BTN_RIGHT}

clicking = False
delay = 0.001
click_type = "left"  # left or right


def set_delay(new_delay):
    global delay
    try:
        value = float(new_delay)
        if not math.isfinite(value) or value < 0:
            raise ValueError
    except (ValueError, TypeError):
        print("Invalid delay input")
        return
    delay = value
    print("Delay:", delay)


def set_click_type(new_type):
    global click_type
    if new_type not in BUTTONS:
        print("Invalid click type")
        return
    click_type = new_type
    print("Click Type:", click_type)


def toggle():
    global clicking
    clicking = not clicking
    print("Clicking:", clicking)


def _find_keyboards():
    """Every readable input device that has an F6 key."""
    keyboards = []
    for path in list_devices():
        try:
            dev = InputDevice(path)
            keys = dev.capabilities().get(e.EV_KEY, [])
        except OSError:  # includes PermissionError
            continue
        if HOTKEY in keys:
            keyboards.append(dev)
        else:
            dev.close()
    return keyboards


def _hotkey_listener(keyboards):
    devices = {dev.fd: dev for dev in keyboards}
    last = 0.0
    while devices:
        readable, _, _ = select.select(list(devices), [], [])
        for fd in readable:
            try:
                for ev in devices[fd].read():
                    # value 1 = key down (0 = up, 2 = autorepeat)
                    if ev.type == e.EV_KEY and ev.code == HOTKEY and ev.value == 1:
                        now = time.monotonic()
                        # debounce: remappers (keyd, kmonad...) can make the
                        # same press show up on two devices at once
                        if now - last > 0.1:
                            last = now
                            toggle()
            except BlockingIOError:
                continue
            except OSError:  # keyboard unplugged
                devices.pop(fd).close()


def run():
    keyboards = _find_keyboards()
    if not keyboards:
        print("No readable keyboard found. Add yourself to the 'input' group "
              "(then log out and back in).")
        return

    try:
        ui = UInput(
            # REL_X/REL_Y make desktops treat this as a real mouse
            {e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT], e.EV_REL: [e.REL_X, e.REL_Y]},
            name="dxrk-autoclicker",
        )
    except (OSError, UInputError) as err:
        print("Could not create virtual mouse:", err)
        print("Load the module (sudo modprobe uinput) and make /dev/uinput writable.")
        return

    threading.Thread(target=_hotkey_listener, args=(keyboards,), daemon=True).start()

    try:
        while True:
            if clicking:
                button = BUTTONS[click_type]
                ui.write(e.EV_KEY, button, 1)
                ui.syn()
                ui.write(e.EV_KEY, button, 0)
                ui.syn()
                time.sleep(delay)
            else:
                # prevents CPU from being maxed when idle
                time.sleep(0.05)
    finally:
        ui.close()


if __name__ == "__main__":
    run()
