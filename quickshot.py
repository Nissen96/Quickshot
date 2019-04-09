import pyscreenshot as ImageGrab
from pynput import mouse, keyboard
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk, ImageDraw
import os.path

CONFIG_FILE = "{}/.config".format(os.path.dirname(os.path.realpath(__file__)))


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


def parent_dir(path):
    return os.path.abspath(os.path.join(path, os.pardir))


def get_previous_path():
    try:
        with open(CONFIG_FILE, "r") as f:
            return f.read()
    except IOError:
        return "."


def set_previous_path(path):
    with open(CONFIG_FILE, "w") as f:
        f.write(path)


class Lens:
    """
    Class for zoom lens to set values and perform calculations only once
    """
    def __init__(self, canvas):
        self.canvas = canvas

        # Settings
        self.selection_width = 10
        self.selection_height = 10
        self.scale = 15
        self.width = self.scale * self.selection_width
        self.height = self.scale * self.selection_height
        self.lens_offset = 10

        # Create circular mask to make lens circular
        self.mask = Image.new("L", (self.width, self.height))
        self.draw = ImageDraw.Draw(self.mask)
        self.draw.ellipse((0, 0) + self.mask.size, fill="#fff")

        # Image must be saved as variable to be persistent
        self.lens_img = None

    def draw_at(self, img, msx, msy):
        self.init()
        self.move_to(img, msx, msy)

    def init(self):
        # Initialize drawings - means they can just be moved at each mouse move
        self.canvas.create_image(0, 0, image=self.lens_img, anchor=tk.NW, tag=("lens", "lensimg"))

        # Imitate center lines on lens
        self.canvas.create_line(0, 0, 0, 0, width=2, fill="#adc0b5", tags=("lens", "hcln"))
        self.canvas.create_line(0, 0, 0, 0, width=2, fill="#adc0b5", tags=("lens", "vcln"))

        # Imitate cursor on lens (black cross on white cross)
        self.canvas.create_line(0, 0, 0, 0, width=8, tags=("lens", "whln"), fill="#fff")
        self.canvas.create_line(0, 0, 0, 0, width=8, tags=("lens", "wvln"), fill="#fff")
        self.canvas.create_line(0, 0, 0, 0, width=4, tags=("lens", "bhln"))
        self.canvas.create_line(0, 0, 0, 0, width=4, tags=("lens", "bvln"))

    def move_to(self, img, msx, msy):
        cropped = img.crop((
            msx - self.selection_width / 2,
            msy - self.selection_height / 2,
            msx + self.selection_height / 2,
            msy + self.selection_height / 2
        ))

        zoomed = Image.new(cropped.mode, (self.width, self.height))
        pixels = []
        for y in range(self.selection_height):
            for _ in range(self.scale):
                for x in range(self.selection_width):
                    pixel = cropped.getpixel((x, y))
                    for _ in range(self.scale):
                        pixels.append(pixel)

        zoomed.putdata(pixels)
        zoomed.putalpha(self.mask)

        self.canvas.delete("lensimg")
        self.lens_img = ImageTk.PhotoImage(zoomed)
        self.canvas.create_image(
            msx + self.lens_offset,
            msy + self.lens_offset,
            image=self.lens_img, anchor=tk.NW, tag="lensimg"
        )

        xcenter = msx + self.width / 2 + self.lens_offset
        ycenter = msy + self.height / 2 + self.lens_offset

        self.canvas.coords("hcln", [xcenter - self.width / 2, ycenter, xcenter + self.width / 2, ycenter])
        self.canvas.coords("vcln", [xcenter, ycenter - self.height / 2, xcenter, ycenter + self.height / 2])
        self.canvas.coords("whln", [xcenter - 30, ycenter, xcenter + 30, ycenter])
        self.canvas.coords("wvln", [xcenter, ycenter - 30, xcenter, ycenter + 30])
        self.canvas.coords("bhln", [xcenter - 28, ycenter, xcenter + 28, ycenter])
        self.canvas.coords("bvln", [xcenter, ycenter - 28, xcenter, ycenter + 28])

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
        self.screenshot = ImageGrab.grab(backend="scrot")
        self.screenshotimg = ImageTk.PhotoImage(self.screenshot)

        # Fill the window with a canvas with the screenshot
        self.canvas = tk.Canvas(self.tk, cursor="cross")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.screenshotimg)

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

        self.lens = Lens(self.canvas)
        self.lens.draw_at(self.screenshot, msx, msy)

        self.x = self.y = 0
        self.selection = None

        # Enable keyboard listener for moving mouse with arrow keys
        kbd = keyboard.Listener(
            on_press=on_press,
            suppress=False
        )
        kbd.start()

    def draw_selection(self, x1, y1, x2, y2):
        fill = self.tk.winfo_rgb("#d8f0e2") + (100,)
        img = Image.new("RGBA", (x2-x1, y2-y1), fill)
        self.selection = ImageTk.PhotoImage(img)
        self.canvas.create_image(x1, y1, image=self.selection, anchor=tk.NW, tag="selection")
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="#adc0b5", tag="selection")

    def on_motion(self, event):
        # Update lens
        self.lens.move_to(self.screenshot, event.x, event.y)

        # Update guiding lines
        self.canvas.coords(self.hline, [0, event.y, self.screenwidth, event.y])
        self.canvas.coords(self.vline, [event.x, 0, event.x, self.screenheight])

    def on_button_press(self, event):
        # Click = start grabbing
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
        self.lens.remove()
        self.canvas.update()

        im = ImageGrab.grab(bbox=(self.x, self.y, event.x, event.y), backend="scrot")

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
            set_previous_path(parent_dir(path))
            self.end()
        else:
            msx, msy = self.tk.winfo_pointerxy()
            self.lens.draw_at(self.screenshot, msx, msy)

    def end(self, _=None):
        self.tk.destroy()


def main():
    qs = Quickshot()
    qs.tk.mainloop()


if __name__ == "__main__":
    main()
