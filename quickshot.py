import pyscreenshot as ImageGrab
from pynput import mouse, keyboard
import tkinter as tk
from PIL import ImageTk


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


class Quickshot:
    def __init__(self):
        # Initialize full screen window
        self.tk = tk.Tk()
        self.tk.attributes("-fullscreen", True)

        # Take a screenshot of the current screen
        self.screenshot = ImageTk.PhotoImage(ImageGrab.grab(backend="scrot"))

        # Fill the window with a canvas with the screenshot
        self.canvas = tk.Canvas(self.tk, cursor="cross")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.screenshot)

        # ESCAPE = quit
        self.tk.bind("<Escape>", self.end)

        # Mouse bindings for click, drag and release
        self.canvas.bind("<B1-Motion>", self.on_button_move)
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.x = self.y = 0

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
        self.canvas.create_rectangle(event.x, event.y, event.x, event.y, fill="#d8f0e2", outline="#adc0b5", tag="selection")

    def on_button_move(self, event):
        # Update rectangle coordinates when moving mouse
        self.canvas.coords("selection", [self.x, self.y, event.x, event.y])

    def on_button_release(self, event):
        # Upon release, remove box, screenshot selection and save
        self.canvas.delete("selection")
        self.canvas.update()
        im = ImageGrab.grab(bbox=(self.x, self.y, event.x, event.y), backend="scrot")
        im.save("testing.png")
        self.end()

    def end(self, event=None):
        self.tk.destroy()


def main():
    qs = Quickshot()
    qs.tk.mainloop()


if __name__ == "__main__":
    main()
