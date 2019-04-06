import pyscreenshot as ImageGrab
from pynput import mouse, keyboard
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import os.path

CONFIG_FILE = "{}/.config".format(os.path.dirname(os.path.realpath(__file__)))

"""
Allows user to move mouse 1 pixel at a time with the arrow keys
while performing the selection
"""
def on_press(key):
    ms = mouse.Controller()
    if key == keyboard.Key.up:
        ms.move(0, -1)
    elif key == keyboard.Key.down:
        ms.move(0, 1)
    elif key == keyboard.Key.left:
        ms.move(-1, 0)
    elif key == keyboard.Key.right:
        ms.move(1, 0)


def parent_dir(path):
    return os.path.abspath(os.path.join(path, os.pardir))


class Quickshot:
    def __init__(self):
        # Initialize full screen window
        self.tk = tk.Tk()
        self.tk.attributes("-fullscreen", True)

        # Set screen size
        self.screenwidth = self.tk.winfo_screenwidth()
        self.screenheight = self.tk.winfo_screenheight()

        # Take a screenshot of the current screen
        self.screenshot = ImageTk.PhotoImage(ImageGrab.grab(backend="scrot"))

        # Fill the window with a canvas with the screenshot
        self.canvas = tk.Canvas(self.tk, cursor="cross")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.screenshot)

        # ESCAPE = quit
        self.tk.bind("<Escape>", self.end)

        # Mouse bindings for click, drag and release
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<B1-Motion>", self.on_button_move)
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        # Initialize horizontal and vertical line at mouse pointer
        msx, msy = self.tk.winfo_pointerxy()
        self.hline = self.canvas.create_line(0, msy, self.screenwidth, msy, fill="#adc0b5", tag="line")
        self.vline = self.canvas.create_line(msx, 0, msx, self.screenheight, fill="#adc0b5", tag="line")

        self.x = self.y = 0
        self.selection = None

    def draw_selection(self, x1, y1, x2, y2):
        fill = self.tk.winfo_rgb("#d8f0e2") + (100,)
        img = Image.new("RGBA", (x2-x1, y2-y1), fill)
        self.selection = ImageTk.PhotoImage(img)
        self.canvas.create_image(x1, y1, image=self.selection, anchor=tk.NW, tag="selection")
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="#adc0b5", tag="selection")

    def on_motion(self, event):
        self.canvas.coords(self.hline, [0, event.y, self.screenwidth, event.y])
        self.canvas.coords(self.vline, [event.x, 0, event.x, self.screenheight])

    def on_button_press(self, event):
        # Click = start grabbing
        # Enable keyboard listener for moving mouse with arrow keys
        kbd = keyboard.Listener(
            on_press=on_press,
            suppress=False
        )
        kbd.start()

        # Set start coordinates
        self.x = event.x
        self.y = event.y

        # Initialize rectangle
        self.draw_selection(event.x, event.y, event.x, event.y)

    def on_button_move(self, event):
        # Update selection upon mouse move
        self.canvas.delete("selection")
        self.draw_selection(self.x, self.y, event.x, event.y)

        # Continue moving lines
        self.on_motion(event)

    def on_button_release(self, event):
        # Upon release, remove box and lines and screenshot selection
        self.canvas.delete("selection")
        self.canvas.delete("line")
        self.canvas.update()
        im = ImageGrab.grab(bbox=(self.x, self.y, event.x, event.y), backend="scrot")

        # Get filename from user
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=(("png files", "*.png"), ("all files", "*.*")),
            initialdir=self.get_previous_path(),
            title="Select file"
        )

        if path:
            # Save file and cache parent folder for next use
            im.save(path)
            self.set_previous_path(parent_dir(path))
            self.end()

    def end(self, event=None):
        self.tk.destroy()

    def get_previous_path(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                return f.read()
        except IOError:
            return "."

    def set_previous_path(self, path):
        with open(CONFIG_FILE, "w") as f:
            f.write(path)


def main():
    qs = Quickshot()
    qs.tk.mainloop()


if __name__ == "__main__":
    main()
