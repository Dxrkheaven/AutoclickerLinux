import time
import sys
from evdev import InputDevice, ecodes, UInput, AbsInfo

# Configuration
delay = 0.001
clicking = False
click_type = "left"  # "left" or "right"

def find_keyboard_device():
    """Automatically find a connected keyboard input device."""
    from evdev import list_devices, InputDevice
    devices = [InputDevice(path) for path in list_devices()]
    for dev in devices:
        caps = dev.capabilities()
        # Check if the device has keys and specifically the F6 key (KEY_F6)
        if ecodes.EV_KEY in caps and ecodes.KEY_F6 in caps[ecodes.EV_KEY]:
            return dev
    return None

def run():
    global clicking, delay, click_type

    # Setup virtual mouse using uinput
    caps = {
        ecodes.EV_KEY: [ecodes.BTN_LEFT, ecodes.BTN_RIGHT],
    }
    
    try:
        ui = UInput(caps, name="auto-clicker", vendor=0x1234, product=0x5678)
    except Exception as e:
        print(f"Failed to create UInput device. Are you running as root or is /dev/uinput accessible? Error: {e}")
        sys.exit(1)

    # Find keyboard
    kb = find_keyboard_device()
    if not kb:
        print("Error: Could not find a keyboard device with F6 capability. Please specify one manually.")
        sys.exit(1)

    print(f"Using keyboard device: {kb.name} ({kb.path})")
    print("Press F6 to toggle clicking. Press Ctrl+C to exit.")

    # Grab the keyboard device so key presses are intercepted (optional, comment out if you don't want to grab)
    # kb.grab()

    try:
        # We'll use non-blocking reads or check select, but since we need a loop that 
        # clicks rapidly when enabled, we can use select with a timeout equal to our delay.
        import select
        
        while True:
            r, w, x = select.select([kb], [], [], 0 if clicking else 0.05)
            
            if r:
                for event in kb.read():
                    if event.type == ecodes.EV_KEY and event.code == ecodes.KEY_F6:
                        if event.value == 1:  # Key down
                            clicking = not clicking
                            print("Clicking:", clicking)

            if clicking:
                btn = ecodes.BTN_LEFT if click_type == "left" else ecodes.BTN_RIGHT
                # Press and release
                ui.write(ecodes.EV_KEY, btn, 1)
                ui.syn()
                ui.write(ecodes.EV_KEY, btn, 0)
                ui.syn()
                time.sleep(delay)

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        ui.close()

if __name__ == "__main__":
    run()
