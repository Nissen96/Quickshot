import numpy as np
import pyscreenshot as ImageGrab
import tkinter as tk

from pathlib import Path
from PIL import Image, ImageTk, ImageDraw
from pynput import mouse, keyboard
from tkinter import filedialog

CONFIG_FILE = Path.home() / ".quickshot"


def on_press(key):
    """
    Allows user to move mouse 1 pixel at a time with the arrow keys
    while performing the selection
    """
    ms = mouse.Controller()
    if key == keyboard.Key.up:
        ms.move(0, -1)
    elif key == keyboard.Key.down:
        ms.move(0, 1)
    elif key == keyboard.Key.left:
        ms.move(-1, 0)
    elif key == keyboard.Key.right:
        ms.move(1, 0)


def get_previous_path():
    # Get cached file location of previously saved screenshot
    try:
        with open(CONFIG_FILE, "r") as f:
            return f.read()
    except IOError:
        return "."


def set_previous_path(path):
    # Cache file location of saved screenshot
    with open(CONFIG_FILE, "w") as f:
        f.write(str(path))


def order_coords(x1, y1, x2, y2):
    return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)


def get_anchor(x1, y1, x2, y2):
    return ((tk.SE, tk.SW), (tk.NE, tk.NW))[y1 > y2][x1 > x2]


def broadcast_tile(arr, tile):
    x, y = arr.shape
    return np.broadcast_to(
        arr.reshape(x, 1, y, 1), (x, tile, y, tile)
    ).reshape(x * tile, y * tile)


class Lens:
    """
    Lens for zooming in around mouse pointer
    to easily see exactly which pixels are selected
    """

    def __init__(self, canvas):
        self.canvas = canvas

        # Settings for selection size, zoom scale and lens size
        self.selection_width = 10
        self.selection_height = 10
        self.scale = 15
        self.width = self.scale * self.selection_width
        self.height = self.scale * self.selection_height
        self.lens_offset = 10 + self.width / 2

        # Create circular mask to make lens circular
        self.mask = Image.new("L", (self.width, self.height))
        self.draw = ImageDraw.Draw(self.mask)
        self.draw.ellipse((0, 0) + self.mask.size, fill="#fff")

        # Image must be saved as variable to be persistent
        self.lens_img = None

    def draw_at(self, img, msx, msy):
        # Initialize image and shapes and move to mouse pointer
        self.init()
        self.move_to(img, msx, msy)

    def init(self):
        # Initialize drawings - means they can just be moved at each mouse move
        self.canvas.create_image(0, 0, image=self.lens_img, anchor=tk.NW, tag="lensimg")

        # Imitate center lines on lens
        self.canvas.create_line(0, 0, 0, 0, width=2, fill="#adc0b5", tags=("lens", "hcln"))
        self.canvas.create_line(0, 0, 0, 0, width=2, fill="#adc0b5", tags=("lens", "vcln"))

        # Imitate cursor on lens (black cross on white cross)
        self.canvas.create_line(0, 0, 0, 0, width=8, tags=("lens", "whln"), fill="#fff")
        self.canvas.create_line(0, 0, 0, 0, width=8, tags=("lens", "wvln"), fill="#fff")
        self.canvas.create_line(0, 0, 0, 0, width=4, tags=("lens", "bhln"))
        self.canvas.create_line(0, 0, 0, 0, width=4, tags=("lens", "bvln"))

    def move_to(self, img, msx, msy, anchor=tk.SE):
        # Get cropped image around mouse and zoom in by creating a block of each pixel
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        cropped_pixels = np.array([
            [img.getpixel((x, y)) if 0 <= x < cw and 0 <= y < ch else (20, 20, 20)  # Show black when outside screen
             for x in range(msx - self.selection_width // 2, msx + self.selection_width // 2)]
            for y in range(msy - self.selection_height // 2, msy + self.selection_height // 2)
        ], dtype="i,i,i")
        pixel_map = [*map(tuple, broadcast_tile(cropped_pixels, self.scale).flatten())]

        # Create a zoomed in version of the cropped image and add circular mask
        zoomed = Image.new(img.mode, (self.width, self.height))
        zoomed.putdata(pixel_map)
        zoomed.putalpha(self.mask)

        xoffset = self.lens_offset if anchor in (tk.NE, tk.SE) else -self.lens_offset
        yoffset = -self.lens_offset if anchor in (tk.SW, tk.SE) else self.lens_offset

        # Replace previous zoomed lens image with new
        self.canvas.delete("lensimg")
        self.lens_img = ImageTk.PhotoImage(zoomed)
        self.canvas.create_image(
            msx + xoffset,
            msy + yoffset,
            image=self.lens_img, tag="lensimg"
        )

        xcenter = msx + xoffset
        ycenter = msy + yoffset

        # Update coordinate of each line
        self.canvas.coords("hcln", [xcenter - self.width / 2, ycenter, xcenter + self.width / 2, ycenter])
        self.canvas.coords("vcln", [xcenter, ycenter - self.height / 2, xcenter, ycenter + self.height / 2])
        self.canvas.coords("whln", [xcenter - 30, ycenter, xcenter + 30, ycenter])
        self.canvas.coords("wvln", [xcenter, ycenter - 30, xcenter, ycenter + 30])
        self.canvas.coords("bhln", [xcenter - 28, ycenter, xcenter + 28, ycenter])
        self.canvas.coords("bvln", [xcenter, ycenter - 28, xcenter, ycenter + 28])

        # Image was replaced = added on top - raise moved lines on top of this
        self.canvas.tag_raise("lens")

    def remove(self):
        self.canvas.delete("lensimg")
        self.canvas.delete("lens")


class Quickshot:
    def __init__(self):
        # Initialize full screen window
        self.tk = tk.Tk()
        self.tk.attributes("-fullscreen", True)

        # Set screen size
        self.screenwidth = self.tk.winfo_screenwidth()
        self.screenheight = self.tk.winfo_screenheight()

        # Take a screenshot of the current screen
        self.screenshot = ImageGrab.grab()
        self.screenshotimg = ImageTk.PhotoImage(self.screenshot)

        # Fill the window with a canvas with the screenshot
        self.canvas = tk.Canvas(self.tk, cursor="cross")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.screenshotimg)

        # ESCAPE = quit
        self.tk.bind("<Escape>", self.end)

        # Mouse bindings for move, click, drag and release
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<B1-Motion>", self.on_button_move)
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        # Enable keyboard listener for moving mouse with arrow keys
        kbd = keyboard.Listener(
            on_press=on_press,
            suppress=False
        )
        kbd.start()

        # Initialize horizontal and vertical line at mouse pointer
        msx, msy = self.tk.winfo_pointerxy()
        self.hline = self.canvas.create_line(0, msy, self.screenwidth, msy, fill="#adc0b5", tag="line")
        self.vline = self.canvas.create_line(msx, 0, msx, self.screenheight, fill="#adc0b5", tag="line")

        # Draw zoom lens
        self.lens = Lens(self.canvas)
        self.lens.draw_at(self.screenshot, msx, msy)

        self.x = self.y = 0
        self.selection = None

    def draw_selection(self, x1, y1, x2, y2):
        # Ensure coordinates are valid
        x1, y1, x2, y2 = order_coords(x1, y1, x2, y2)

        # Simulate a transparent rectangle with a transparent image
        fill = self.tk.winfo_rgb("#d8f0e2") + (100,)
        img = Image.new("RGBA", (x2 - x1, y2 - y1), fill)
        self.selection = ImageTk.PhotoImage(img)
        self.canvas.create_image(x1, y1, image=self.selection, anchor=tk.NW, tag="selection")

        # Border
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="#adc0b5", tag="selection")

    def on_motion(self, event):
        anchor = get_anchor(self.x, self.y, event.x, event.y)

        # Update lens
        self.lens.move_to(self.screenshot, event.x, event.y, anchor=anchor)

        # Update guidelines
        self.canvas.coords(self.hline, [0, event.y, self.screenwidth, event.y])
        self.canvas.coords(self.vline, [event.x, 0, event.x, self.screenheight])

    def on_button_press(self, event):
        # Click = start grabbing
        # Set start coordinates
        self.x = event.x
        self.y = event.y

        # Show currently selected window
        self.draw_selection(event.x, event.y, event.x, event.y)

    def on_button_move(self, event):
        # Update selection upon mouse move
        self.canvas.delete("selection")
        self.draw_selection(self.x, self.y, event.x, event.y)

        # Update lines
        self.on_motion(event)

    def on_button_release(self, event):
        # Upon release, remove everything but the screenshot
        self.canvas.delete("selection")
        self.canvas.delete("line")
        self.lens.remove()
        self.canvas.update()

        # Create the actual screenshot of the selection
        im = ImageGrab.grab(bbox=order_coords(self.x, self.y, event.x, event.y))

        # Get filename from user
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=(("png files", "*.png"), ("all files", "*.*")),
            initialdir=get_previous_path(),
            title="Select file"
        )

        if path:
            # Save file and cache parent folder for next use
            im.save(path)
            set_previous_path(Path(path).parent)
            self.end()
        else:
            # If cancel pressed, redraw lens and keep running
            msx, msy = self.tk.winfo_pointerxy()
            self.lens.draw_at(self.screenshot, msx, msy)

    def end(self, _=None):
        self.tk.destroy()


def main():
    qs = Quickshot()
    qs.tk.mainloop()


if __name__ == "__main__":
    main()
