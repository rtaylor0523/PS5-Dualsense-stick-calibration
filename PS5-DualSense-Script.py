import tkinter as tk
from tkinter import messagebox
import hid
import threading
import time
import json
import os

# === DEVICE SETUP ===
dev = None
VALID_DEVICE_IDS = [
    (0x054c, 0x0ce6),  # DualSense
    (0x054c, 0x0df2),  # Updated firmware
    (0x054c, 0x0da5),  # DualSense Edge
]

BACKUP_FILE = "calibration_backup.json"

# === Find DualSense Controller ===
def find_dualsense():
    for d in hid.enumerate():
        if (d['vendor_id'], d['product_id']) in VALID_DEVICE_IDS:
            iface = d.get('interface_number', -1)
            if iface >= 2:
                return d
    return None

def open_dualsense():
    info = find_dualsense()
    if info is None:
        return None
    h = hid.device()
    h.open_path(info['path'])
    h.set_nonblocking(False)
    return h

def ensure_device_connected():
    if dev is None:
        messagebox.showerror("Device Error", "No controller connected.")
        return False
    return True

# === HID Helpers ===
def hid_write(report_id, data):
    buf = [report_id] + list(data)
    dev.write(buf)

def hid_read(expected_len=64, timeout=1.0):
    start = time.time()
    while time.time() - start < timeout:
        r = dev.read(expected_len)
        if r:
            return r
    raise IOError("No response from device within timeout.")

# === CALIBRATION FUNCTIONS ===
def do_stick_center_calibration():
    if not ensure_device_connected():
        return
    try:
        deviceId = 1
        targetId = 1

        hid_write(0x82, [1, deviceId, targetId])
        k = hid_read(4)
        if k != [deviceId, targetId, 1, 0xff]:
            print(f"Warning: Unexpected state: {k}")

        def on_sample():
            hid_write(0x82, [3, deviceId, targetId])
            r = hid_read(4)
            messagebox.showinfo("Sampled", f"Sampled response: {r}")

        def on_write():
            offset = deadzone_offset.get()
            hid_write(0x82, [3, deviceId, targetId])
            r = hid_read(4)

            centered = r.copy()
            if centered[2] > 128:
                centered[2] = max(centered[2] - offset, 0)
            elif centered[2] < 128:
                centered[2] = min(centered[2] + offset, 255)

            hid_write(0x82, [2] + centered[:3])
            messagebox.showinfo("Done", f"Center calibration saved with offset: {offset}")
            sample_win.destroy()

        sample_win = tk.Toplevel(root)
        sample_win.title("Center Calibration")
        tk.Label(sample_win, text='Press "Record", Then "Save"').pack(pady=5)
        tk.Button(sample_win, text="Record", command=on_sample).pack(pady=5)
        tk.Button(sample_win, text="Save", command=on_write).pack(pady=5)

    except Exception as e:
        messagebox.showerror("Error", str(e))

def do_stick_minmax_calibration():
    if not ensure_device_connected():
        return
    try:
        deviceId = 1
        targetId = 2

        hid_write(0x82, [1, deviceId, targetId])
        k = hid_read(4)

        if k != [deviceId, targetId, 1, 0xff]:
            print(f"Warning: Unexpected state: {k}")

        messagebox.showinfo("Move Sticks", "Move sticks to full range, then press OK.")
        hid_write(0x82, [2, deviceId, targetId])
        messagebox.showinfo("Done", "Min-max calibration complete.")
    except Exception as e:
        messagebox.showerror("Error", str(e))

# === BACKUP / RESTORE ===
def backup_calibration():
    try:
        deviceId = 1
        targetIds = [1, 2]
        backup = {}

        for tid in targetIds:
            hid_write(0x82, [1, deviceId, tid])
            r = hid_read(4)
            if len(r) == 4 and r[0] == deviceId and r[1] == tid:
                backup[f"{tid}"] = r
            else:
                raise Exception(f"Unexpected response while backing up: {r}")

        with open(BACKUP_FILE, "w") as f:
            json.dump(backup, f)

        print("Calibration backup saved.")
        btn_restore.config(state="normal")
    except Exception as e:
        print(f"Backup failed: {e}")

def restore_calibration():
    try:
        if not ensure_device_connected():
            return
        if not os.path.exists(BACKUP_FILE):
            messagebox.showerror("No Backup", "No backup file found.")
            return

        with open(BACKUP_FILE, "r") as f:
            backup = json.load(f)

        unlock_nvs()
        for tid in backup:
            val = backup[tid]
            hid_write(0x82, [2] + val[:3])  # Write original values back
        relock_nvs()

        messagebox.showinfo("Restored", "Calibration restored from backup.")
    except Exception as e:
        messagebox.showerror("Restore Failed", str(e))

# === NVS (Non-Volatile Storage) Access ===
def unlock_nvs():
    if not ensure_device_connected():
        return
    hid_write(0x80, [3, 2, 101, 50, 64, 12])

def relock_nvs():
    if not ensure_device_connected():
        return
    hid_write(0x80, [3, 1])

def run_calibration(func):
    try:
        if make_perm.get():
            unlock_nvs()
        func()
        if make_perm.get():
            relock_nvs()
    except Exception as e:
        messagebox.showerror("Error", str(e))

# === STICK VISUALIZATION ===
stick_pos = {"left": (128, 128), "right": (128, 128)}

def draw_deadzone_visual():
    canvas.delete("all")
    radius = deadzone_offset.get() * 2
    scale = 40 / 128  # pixel scale

    centers = {"left": (75, 90), "right": (225, 90)}
    for side in ["left", "right"]:
        cx, cy = centers[side]

        # Draw deadzone
        canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                           fill="lightgray", outline="black")

        # Crosshairs
        canvas.create_line(cx - 25, cy, cx + 25, cy, fill="gray")
        canvas.create_line(cx, cy - 25, cx, cy + 25, fill="gray")

        # Live stick dot
        raw_x, raw_y = stick_pos[side]
        dx = int((raw_x - 128) * scale)
        dy = int((raw_y - 128) * scale)
        canvas.create_oval(cx + dx - 3, cy + dy - 3, cx + dx + 3, cy + dy + 3,
                           fill="green", outline="black")

        canvas.create_text(cx, cy + 40, text=f"{side.capitalize()} Stick", font=("Arial", 8))

def poll_stick_positions():
    global dev, stick_pos
    while True:
        if dev:
            try:
                data = dev.read(64)
                if data and len(data) >= 5:
                    lx = data[1]
                    ly = data[2]
                    rx = data[3]
                    ry = data[4]
                    stick_pos["left"] = (lx, ly)
                    stick_pos["right"] = (rx, ry)
                    root.after(0, draw_deadzone_visual)
            except Exception as e:
                print(f"Polling error: {e}")
        time.sleep(0.02)

# === CONNECT CONTROLLER ===
def connect_controller():
    def worker():
        global dev
        try:
            dev = open_dualsense()
            if dev:
                messagebox.showinfo("Success", "DualSense connected!")
                btn_center.config(state="normal")
                btn_range.config(state="normal")
                if not os.path.exists(BACKUP_FILE):
                    backup_calibration()
                else:
                    btn_restore.config(state="normal")
                threading.Thread(target=poll_stick_positions, daemon=True).start()
            else:
                messagebox.showwarning("Not Found", "No DualSense controller found.")
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
    threading.Thread(target=worker, daemon=True).start()

# === GUI ===
root = tk.Tk()
root.title("DualSense Calibration Tool (with Deadzone Offset & Live View)")

tk.Label(root, text="🎮 DualSense Calibration Tool", font=("Arial", 16)).pack(pady=10)
tk.Button(root, text="Connect Controller", command=connect_controller).pack(pady=5)

btn_center = tk.Button(root, text="Center Calibration", command=lambda: run_calibration(do_stick_center_calibration), state="disabled")
btn_center.pack(pady=5)

btn_range = tk.Button(root, text="Range Calibration", command=lambda: run_calibration(do_stick_minmax_calibration), state="disabled")
btn_range.pack(pady=5)

btn_restore = tk.Button(root, text="Restore Calibration", command=restore_calibration, state="disabled")
btn_restore.pack(pady=5)

make_perm = tk.BooleanVar()
tk.Checkbutton(root, text="Make changes permanent", variable=make_perm).pack(pady=5)

# === NEW: Deadzone Offset Slider ===
deadzone_offset = tk.IntVar(value=5)
tk.Label(root, text="Safe Deadzone Offset").pack()
tk.Scale(root, from_=0, to=20, orient="horizontal", variable=deadzone_offset,
         command=lambda x: draw_deadzone_visual()).pack(pady=5)

# === VISUAL STICK DEADZONE CANVAS ===
canvas = tk.Canvas(root, width=300, height=180, bg="white")
canvas.pack(pady=10)

tk.Label(root, text="v0.05 | Realtime Stick View 🎯").pack(pady=10)

draw_deadzone_visual()
root.mainloop()
