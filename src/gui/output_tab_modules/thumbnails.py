import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw, ImageFont
from loguru import logger
from ..utils import resize_image
from .video_actions import show_context_menu, play_video
from .selection import select_video, toggle_selection

def update_output_tab(gui, video, thumbnails, timestamps, duration):
    """Update the output tab with new thumbnails, timestamps, and video duration."""
    logger.debug(f"Updating Output tab for {video} with {len(thumbnails)} thumbnails")
    gui.videos[video] = thumbnails
    gui.video_counter += 1

    frame = None
    for child in gui.output_scrollable_frame.winfo_children():
        if hasattr(child, 'video_path') and child.video_path == video:
            frame = child
            break
    if not frame:
        bg_color = "lightblue" if video in gui.selected_videos else "white"
        frame = tk.Frame(gui.output_scrollable_frame, highlightbackground="black", highlightthickness=1, bg=bg_color)
        frame.pack(fill='x', padx=5, pady=5)
        frame.video_path = video

        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        video_label_text = f"{gui.video_counter}. {Path(video).name} (Duration: {duration_str})"
        tk.Label(frame, text=video_label_text, anchor="nw", justify="left", bg=bg_color).pack(side="top", anchor="nw")

        thumbnail_frame = tk.Frame(frame, bg=bg_color)
        thumbnail_frame.pack()
        var = tk.BooleanVar(value=video in gui.selected_videos)
        checkbutton = tk.Checkbutton(thumbnail_frame, variable=var, command=lambda v=video: toggle_selection(gui, v, var), bg=bg_color)
        checkbutton.pack(side='left')
        checkbutton.var = var

        thumbs_per_column = gui.config.get('thumbnails_per_column')
        num_thumbs = len(thumbnails)
        cols = (num_thumbs + thumbs_per_column - 1) // thumbs_per_column
        original_width = gui.processor.thumbnail_width
        original_height = int(gui.processor.thumbnail_width * 9 / 16)
        text_width_estimate = 50
        canvas_width = (original_width + text_width_estimate) * cols
        text_height_estimate = 20
        canvas_height = (original_height + text_height_estimate) * min(thumbs_per_column, num_thumbs)
        thumbnail_canvas = tk.Canvas(thumbnail_frame, height=canvas_height, width=canvas_width, bg=bg_color)
        thumbnail_canvas.pack(side='left', fill='both', expand=True)

        images, photo_images = [], []
        cache_base = video.parent / "cache" / video.name
        for idx, thumb in enumerate(thumbnails):
            thumb_path = cache_base / thumb
            if thumb_path.exists():
                img = Image.open(thumb_path)
                aspect_ratio = img.width / img.height
                new_width = original_width
                new_height = original_height
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                timestamp = timestamps[idx]
                hours = int(timestamp // 3600)
                minutes = int((timestamp % 3600) // 60)
                seconds = int(timestamp % 60)
                timestamp_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

                draw = ImageDraw.Draw(img)
                try:
                    font = ImageFont.truetype("arial.ttf", 14)
                except IOError:
                    font = ImageFont.load_default()
                text_bbox = draw.textbbox((0, 0), timestamp_str, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                padding = 5
                text_x = new_width - text_width - padding
                text_y = new_height - text_height - padding
                text_x = max(padding, text_x)
                text_y = max(padding, text_y)
                draw.rectangle(
                    (text_x - padding, text_y - padding, text_x + text_width + padding, text_y + text_height + padding),
                    fill=(0, 0, 0, 128)
                )
                draw.text((text_x, text_y), timestamp_str, fill="white", font=font)

                images.append(img)
                photo = ImageTk.PhotoImage(img)
                photo_images.append(photo)
                gui.photo_references.append(photo)

        scroll_frame = tk.Frame(thumbnail_canvas, bg=bg_color)
        thumbnail_canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        thumbnail_canvas.configure(xscrollcommand=lambda *args: None)

        for i, photo in enumerate(photo_images):
            col = i // thumbs_per_column
            row = i % thumbs_per_column
            lbl = tk.Label(scroll_frame, image=photo, bd=0, bg=bg_color)
            lbl.original_image = images[i]
            lbl.current_scale = 1.0
            lbl.is_zoomed = False
            lbl.original_width = original_width + text_width_estimate
            lbl.original_height = original_height + text_height_estimate
            lbl.grid(row=row, column=col, padx=2, pady=2)
            lbl.bind("<Enter>", lambda e, l=lbl: on_enter(gui, e, l, thumbnail_canvas))
            lbl.bind("<Leave>", lambda e, l=lbl, c=thumbnail_canvas: on_leave(gui, e, l, c))
            lbl.bind("<Button-1>", lambda e, v=video: select_video(gui, v, var))
            lbl.bind("<Button-2>", lambda e, v=video: play_video(gui, v))
            lbl.bind("<Double-1>", lambda e, v=video: play_video(gui, v))
            lbl.bind("<Button-3>", lambda e, v=video: show_context_menu(gui, e, v))

        frame.bind("<Button-3>", lambda e, v=video: show_context_menu(gui, e, v))
        thumbnail_frame.bind("<Button-3>", lambda e, v=video: show_context_menu(gui, e, v))
        thumbnail_canvas.bind("<Button-3>", lambda e, v=video: show_context_menu(gui, e, v))

        logger.debug(f"Added frame for {video} to Output tab")
        gui.output_scrollable_frame.update_idletasks()
        gui.output_canvas.configure(scrollregion=gui.output_canvas.bbox("all"))
        logger.debug(f"Updated scroll region for Output tab")
        gui.update_selection_count()
    else:
        bg_color = "lightblue" if video in gui.selected_videos else "white"
        frame.configure(bg=bg_color)
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        video_label_text = f"{gui.video_counter}. {Path(video).name} (Duration: {duration_str})"
        for child in frame.winfo_children():
            if isinstance(child, tk.Label):
                child.configure(text=video_label_text, bg=bg_color)
            elif isinstance(child, tk.Frame):
                child.configure(bg=bg_color)
                for sub_child in child.winfo_children():
                    if isinstance(sub_child, tk.Checkbutton):
                        sub_child.configure(bg=bg_color)
                        sub_child.var.set(video in gui.selected_videos)
                    elif isinstance(sub_child, tk.Canvas):
                        sub_child.configure(bg=bg_color)
                        for item in sub_child.find_all():
                            widget = sub_child.nametowidget(sub_child.itemcget(item, "window"))
                            if isinstance(widget, tk.Frame):
                                widget.configure(bg=bg_color)
                                for sub_sub_child in widget.winfo_children():
                                    sub_sub_child.configure(bg=bg_color)
        gui.update_selection_count()

def on_enter(gui, event, label, canvas):
    """Zoom in on a thumbnail when hovering with Ctrl key."""
    if event.state & 0x0004 and not label.is_zoomed:
        zoom_factor = gui.config.get('zoom_factor')
        img = label.original_image
        new_width, new_height = int(label.original_width * zoom_factor), int((label.original_height - 20) * zoom_factor)
        zoomed_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(zoomed_img)
        label.configure(image=photo)
        if hasattr(label, 'photo'):
            gui.photo_references.remove(label.photo)
        label.photo = photo
        gui.photo_references.append(photo)
        canvas.configure(height=new_height + 20)
        label.is_zoomed = True

def on_leave(gui, event, label, canvas):
    """Revert to original thumbnail size when leaving with Ctrl key."""
    if label.is_zoomed:
        img = label.original_image
        original_width, original_height = label.original_width, label.original_height
        original_img = img.resize((original_width, original_height - 20), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(original_img)
        label.configure(image=photo)
        if hasattr(label, 'photo'):
            gui.photo_references.remove(label.photo)
        label.photo = photo
        gui.photo_references.append(photo)
        canvas.configure(height=original_height)
        label.is_zoomed = False