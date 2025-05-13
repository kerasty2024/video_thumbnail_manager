import tkinter as tk
import os
import shutil
from loguru import logger

def toggle_selection(gui, video, var):
    """Toggle the selection state of a video without rebuilding the entire UI."""
    logger.debug(f"Toggle selection for {video}: var={var.get()}")
    if var.get():
        gui.selected_videos.add(video)
        logger.debug(f"Added {video} to selected_videos")
    else:
        gui.selected_videos.discard(video)
        logger.debug(f"Removed {video} from selected_videos")
    for child in gui.output_scrollable_frame.winfo_children():
        if hasattr(child, 'video_path') and child.video_path == video:
            bg_color = "lightblue" if video in gui.selected_videos else "white"
            child.configure(bg=bg_color)
            for sub_child in child.winfo_children():
                if isinstance(sub_child, tk.Label):
                    sub_child.configure(bg=bg_color)
                elif isinstance(sub_child, tk.Frame):
                    sub_child.configure(bg=bg_color)
                    for sub_sub_child in child.winfo_children():
                        if isinstance(sub_sub_child, tk.Checkbutton):
                            sub_sub_child.configure(bg=bg_color)
                            sub_sub_child.var.set(video in gui.selected_videos)
                        elif isinstance(sub_sub_child, tk.Canvas):
                            sub_child.configure(bg=bg_color)
                            for item in sub_child.find_all():
                                widget = sub_child.nametowidget(sub_child.itemcget(item, "window"))
                                if isinstance(widget, tk.Frame):
                                    widget.configure(bg=bg_color)
                                    for sub_sub_sub_child in widget.winfo_children():
                                        sub_sub_sub_child.configure(bg=bg_color)
            logger.debug(f"Updated UI for {video}: bg_color={bg_color}, selected_videos={gui.selected_videos}")
            break
    gui.update_selection_count()

def select_video(gui, video, var):
    """Toggle video selection with a click."""
    var.set(not var.get())
    toggle_selection(gui, video, var)

def delete_selected(gui):
    """Delete all selected videos from the filesystem and UI, including their caches."""
    for video in gui.selected_videos.copy():
        try:
            os.remove(video)
            cache_dir = video.parent / "cache" / video.name
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                logger.debug(f"Deleted cache directory for {video}: {cache_dir}")
            del gui.videos[video]
            for widget in gui.output_scrollable_frame.winfo_children():
                if hasattr(widget, 'video_path') and widget.video_path == video:
                    widget.destroy()
                    break
        except Exception as e:
            gui.report_error(video, str(e))
    gui.selected_videos.clear()
    gui.output_scrollable_frame.update_idletasks()
    gui.output_canvas.configure(scrollregion=gui.output_canvas.bbox("all"))
    gui.update_selection_count()

def delete_unselected(gui):
    """Delete all unselected videos from the filesystem and UI, including their caches."""
    videos_to_delete = set(gui.videos.keys()) - gui.selected_videos
    for video in videos_to_delete:
        try:
            os.remove(video)
            cache_dir = video.parent / "cache" / video.name
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                logger.debug(f"Deleted cache directory for {video}: {cache_dir}")
            del gui.videos[video]
            for widget in gui.output_scrollable_frame.winfo_children():
                if hasattr(widget, 'video_path') and widget.video_path == video:
                    widget.destroy()
                    break
        except Exception as e:
            gui.report_error(video, str(e))
    gui.selected_videos.clear()
    gui.output_scrollable_frame.update_idletasks()
    gui.output_canvas.configure(scrollregion=gui.output_canvas.bbox("all"))
    gui.update_selection_count()

def clear_all_selection(gui):
    """Clear all video selections."""
    logger.debug(f"Clearing all selections, initial selected_videos: {gui.selected_videos}")
    gui.selected_videos.clear()
    for frame in gui.output_scrollable_frame.winfo_children():
        if hasattr(frame, 'video_path'):
            bg_color = "white"
            frame.configure(bg=bg_color)
            for child in frame.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=bg_color)
                elif isinstance(child, tk.Frame):
                    child.configure(bg=bg_color)
                    for sub_child in child.winfo_children():
                        if isinstance(sub_child, tk.Checkbutton):
                            previous_state = sub_child.var.get()
                            sub_child.var.set(False)
                            sub_child.configure(bg=bg_color)
                            logger.debug(f"Updated checkbutton for {frame.video_path}: previous_state={previous_state}, new_state={sub_child.var.get()}")
                            toggle_selection(gui, frame.video_path, sub_child.var)
                        elif isinstance(sub_child, tk.Canvas):
                            sub_child.configure(bg=bg_color)
                            for item in sub_child.find_all():
                                widget = sub_child.nametowidget(sub_child.itemcget(item, "window"))
                                if isinstance(widget, tk.Frame):
                                    widget.configure(bg=bg_color)
                                    for sub_sub_child in widget.winfo_children():
                                        sub_sub_child.configure(bg=bg_color)
    gui.output_scrollable_frame.update()
    gui.root.update()
    logger.debug(f"Finished clearing selections, final selected_videos: {gui.selected_videos}")
    gui.update_selection_count()