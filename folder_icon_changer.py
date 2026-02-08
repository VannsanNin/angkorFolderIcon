import customtkinter as ctk
import os
import subprocess
from pathlib import Path
from PIL import Image
import cairosvg
import threading
import json
import urllib.request
import webbrowser
from packaging import version

import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return Path(os.path.join(base_path, relative_path))

# Configuration
ICON_DIR = resource_path("icons")
CACHE_DIR = Path.home() / ".cache" / "folder-icon-changer"
PREVIEW_DIR = CACHE_DIR / "previews"
CONVERTED_DIR = CACHE_DIR / "converted"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

APP_VERSION = "0.0.1"
GITHUB_REPO = "https://github.com/VannsanNin/angkorFolderIcon.git" # TODO: Update this

class UpdateChecker:
    @staticmethod
    def check_for_updates(current_version_str):
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(url, headers={"User-Agent": "IconChangerApp"})
            
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    latest_tag = data.get("tag_name", "").lstrip("v")
                    html_url = data.get("html_url", "")
                    
                    if not latest_tag:
                        return None
                        
                    current = version.parse(current_version_str)
                    latest = version.parse(latest_tag)
                    
                    if latest > current:
                        return html_url
            return None
        except Exception as e:
            print(f"Update check failed: {e}")
            return None

class IconChangerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Icon Changer")
        self.geometry("1000x700")

        self.selected_target = None # Can be folder or file path
        self.selected_icon_path = None
        
        # We will keep references to buttons to destroy them on refresh/filter
        self.folder_buttons = []
        self.file_buttons = []

        # Data sources
        self.folder_icons_all = []
        self.file_icons_all = []

        # Lazy Loading State
        self.batch_size = 20
        self.current_display_list = []
        self.loaded_count = 0
        self.is_loading = False
        self.load_id = 0

        # Ensure cache directories exist
        PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
        CONVERTED_DIR.mkdir(parents=True, exist_ok=True)

        self.setup_ui()
        self.start_loading_icons()
        self.check_for_updates_bg()

    def check_for_updates_bg(self):
        threading.Thread(target=self._update_check_thread, daemon=True).start()

    def _update_check_thread(self):
        update_url = UpdateChecker.check_for_updates(APP_VERSION)
        if update_url:
            self.after(0, lambda: self.show_update_button(update_url))

    def show_update_button(self, url):
        self.btn_update = ctk.CTkButton(
            self.sidebar, 
            text="Update Available!", 
            fg_color="#E0a800", 
            text_color="black",
            hover_color="#C09000",
            command=lambda: webbrowser.open(url)
        )
        # Place it above the status label (row 7), pushing status to row 8
        self.btn_update.grid(row=6, column=0, padx=20, pady=(10, 0))
        # Ensure Status is at bottom
        self.status_label.grid(row=8, column=0, padx=20, pady=10)

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar, text="Icon Changer", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.target_type_label = ctk.CTkLabel(self.sidebar, text="Target:", anchor="w")
        self.target_type_label.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.target_label = ctk.CTkLabel(self.sidebar, text="None selected", wraplength=180, text_color="gray", anchor="w", justify="left")
        self.target_label.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")

        # Dynamic Button (Select Folder / Select File) - handled by tab switch logic, 
        # but here we might just have two buttons or one that changes. 
        # Simpler: Two buttons always visible or context sensitive. 
        # Let's make it context sensitive to the active tab.
        self.btn_select = ctk.CTkButton(self.sidebar, text="Select Folder", command=self.select_target)
        self.btn_select.grid(row=3, column=0, padx=20, pady=10)

        self.btn_apply = ctk.CTkButton(self.sidebar, text="Apply Icon", command=self.apply_icon, state="disabled", fg_color="green")
        self.btn_apply.grid(row=4, column=0, padx=20, pady=10)

        self.btn_reset = ctk.CTkButton(self.sidebar, text="Reset Icon", command=self.reset_icon, state="disabled", fg_color="transparent", border_width=2)
        self.btn_reset.grid(row=5, column=0, padx=20, pady=(10, 20))
        
        self.status_label = ctk.CTkLabel(self.sidebar, text=f"Ready (v{APP_VERSION})", text_color="gray", wraplength=180)
        self.status_label.grid(row=8, column=0, padx=20, pady=10)

        # --- Main Area ---
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_rowconfigure(2, weight=1) # Tabview expands
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Search
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", self.on_search)
        self.search_entry = ctk.CTkEntry(self.main_frame, placeholder_text="Search icons...", textvariable=self.search_var)
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 10))

        # Tabs
        self.tabview = ctk.CTkTabview(self.main_frame, command=self.on_tab_change)
        self.tabview.grid(row=2, column=0, sticky="nsew")
        
        self.tab_folders = self.tabview.add("Folders")
        self.tab_files = self.tabview.add("Files")
        
        # Scrollable Frames inside tabs
        self.scroll_folders = ctk.CTkScrollableFrame(self.tab_folders, label_text="Folder Icons")
        self.scroll_folders.pack(fill="both", expand=True)
        self.scroll_folders.grid_columnconfigure((0,1,2,3,4), weight=1)

        self.scroll_files = ctk.CTkScrollableFrame(self.tab_files, label_text="File Icons")
        self.scroll_files.pack(fill="both", expand=True)
        self.scroll_files.grid_columnconfigure((0,1,2,3,4), weight=1)

        # Start scroll check loop
        self.check_scroll_loop()

    def check_scroll_loop(self):
        try:
            current_tab = self.tabview.get()
            if current_tab == "Folders":
                scroll_frame = self.scroll_folders
            else:
                scroll_frame = self.scroll_files
            
            # yview returns (top_fraction, bottom_fraction)
            # If bottom_fraction is near 1.0, we are at the bottom
            _, bottom = scroll_frame._parent_canvas.yview()
            if bottom > 0.90: # Trigger a bit earlier
                self.load_more_icons()
        except Exception:
            pass
        finally:
            # Check every 300ms
            self.after(300, self.check_scroll_loop)

    def start_loading_icons(self):
        self.status_label.configure(text="Loading icons...")
        threading.Thread(target=self.load_icons_thread, daemon=True).start()

    def load_icons_thread(self):
        if not ICON_DIR.exists():
            self.after(0, lambda: self.status_label.configure(text="Error: 'icons' dir missing"))
            return

        # Separate icons
        all_svgs = sorted(list(ICON_DIR.glob("*.svg")))
        
        for svg in all_svgs:
            if svg.name.startswith("folder-"):
                self.folder_icons_all.append(svg)
            else:
                self.file_icons_all.append(svg)

        # Generate thumbnails for all (this takes time, maybe do lazy load? 
        # For now, we process all but update status).
        # Actually, let's just trigger population of the current tab first.
        self.after(0, self.refresh_visible_icons)
        self.after(0, lambda: self.status_label.configure(text="Icons found. Rendering..."))

    def on_tab_change(self):
        tab_name = self.tabview.get()
        if tab_name == "Folders":
            self.btn_select.configure(text="Select Folder")
        else:
            self.btn_select.configure(text="Select File")
        
        # clear selection if incompatible? Maybe nice to keep if switching back.
        # But for UI clarity, let's reset target if it doesn't match type.
        # Actually, let's just keep the selection logic flexible.
        
        self.refresh_visible_icons()

    def on_search(self, *args):
        # Debounce could be good, but let's try direct first
        self.refresh_visible_icons()

    def refresh_visible_icons(self):
        current_tab = self.tabview.get()
        query = self.search_var.get().lower()

        if current_tab == "Folders":
            source_list = self.folder_icons_all
            btn_list = self.folder_buttons
        else:
            source_list = self.file_icons_all
            btn_list = self.file_buttons

        # Clear existing buttons
        for btn in btn_list:
            btn.destroy()
        btn_list.clear()

        # Update ID to invalidate old threads
        self.load_id += 1

        # Filter
        self.current_display_list = [p for p in source_list if query in p.stem.lower()]
        self.loaded_count = 0
        
        # Trigger initial load
        self.load_more_icons()

    def load_more_icons(self):
        if self.is_loading:
            return
        
        if self.loaded_count >= len(self.current_display_list):
            return

        self.is_loading = True
        
        current_tab = self.tabview.get()
        if current_tab == "Folders":
            parent_frame = self.scroll_folders
            btn_list = self.folder_buttons
        else:
            parent_frame = self.scroll_files
            btn_list = self.file_buttons

        # Determine batch
        start_index = self.loaded_count
        end_index = min(self.loaded_count + self.batch_size, len(self.current_display_list))
        batch = self.current_display_list[start_index:end_index]
        
        # Capture current load_id
        current_load_id = self.load_id

        # Start thread
        threading.Thread(target=self.populate_icons_thread, args=(batch, start_index, current_load_id, parent_frame, btn_list), daemon=True).start()
        
        self.loaded_count = end_index

    def populate_icons_thread(self, display_list, start_index, load_id, parent_frame, btn_list):
        max_cols = 5
        current_idx = start_index

        for svg_path in display_list:
            # Check if obsolete
            if load_id != self.load_id:
                self.is_loading = False
                return

            # Calc row/col based on absolute index
            row = current_idx // max_cols
            col = current_idx % max_cols

            # Prepare image
            preview_path = PREVIEW_DIR / f"{svg_path.stem}.png"
            if not preview_path.exists():
                try:
                    cairosvg.svg2png(url=str(svg_path), write_to=str(preview_path), output_width=64, output_height=64)
                except:
                    continue
            
            # Add to UI main thread
            self.after(0, lambda p=preview_path, s=svg_path, r=row, c=col, lid=load_id, pf=parent_frame, bl=btn_list: self.add_button(p, s, r, c, lid, pf, bl))
            
            current_idx += 1
        
        self.is_loading = False

    def add_button(self, preview_path, svg_path, row, col, load_id, parent_frame, btn_list):
        if load_id != self.load_id:
            return

        try:
            name = svg_path.stem.replace("folder-", "")
            if len(name) > 15:
                name = name[:12] + "..."

            img = ctk.CTkImage(light_image=Image.open(preview_path), dark_image=Image.open(preview_path), size=(48, 48))
            
            btn = ctk.CTkButton(
                parent_frame, 
                text=name, 
                image=img, 
                compound="top", 
                fg_color="transparent", 
                width=100,
                height=100,
                command=lambda p=svg_path: self.select_icon(p)
            )
            btn.grid(row=row, column=col, padx=5, pady=5)
            btn_list.append(btn)
            
            # Bind scroll events to the button to ensure scrolling works when hovering
            # Linux
            btn.bind("<Button-4>", lambda e: self._on_mouse_scroll(e, parent_frame, -1))
            btn.bind("<Button-5>", lambda e: self._on_mouse_scroll(e, parent_frame, 1))
            # Windows/MacOS
            btn.bind("<MouseWheel>", lambda e: self._on_mouse_scroll(e, parent_frame, 0))
            
        except Exception:
            pass

    def _on_mouse_scroll(self, event, scroll_frame, direction):
        # direction: -1 (up), 1 (down), 0 (mousewheel delta)
        try:
            if direction == 0:
                # Windows/MacOS
                scroll_frame._parent_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            else:
                # Linux
                scroll_frame._parent_canvas.yview_scroll(direction, "units")
            
            # Optional: Check load trigger immediately for responsiveness
            self.check_scroll_position_manual(scroll_frame)
        except:
            pass
            
    def check_scroll_position_manual(self, scroll_frame):
         try:
            _, bottom = scroll_frame._parent_canvas.yview()
            if bottom > 0.90:
                self.load_more_icons()  
         except:
             pass

    def select_target(self):
        tab = self.tabview.get()
        path = ""
        if tab == "Folders":
            path = ctk.filedialog.askdirectory()
        else:
            path = ctk.filedialog.askopenfilename()
        
        if path:
            self.selected_target = path
            self.target_label.configure(text=os.path.basename(path), text_color=("black", "white"))
            self.check_ready()
            self.btn_reset.configure(state="normal")
            
            # Auto-suggest icon based on extension if in Files tab
            if tab == "Files":
                self.try_auto_select_icon(path)

    def try_auto_select_icon(self, path):
        ext = Path(path).suffix.lower().lstrip(".")
        if not ext:
            return

        # Common mappings (extension -> icon name)
        # Note: Many work directly (e.g. "json" -> "json.svg")
        # but some need aliases.
        mappings = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "jsx": "react",
            "tsx": "react_ts",
            "md": "markdown",
            "rb": "ruby",
            "rs": "rust",
            "go": "go",
            "java": "java",
            "c": "c",
            "cpp": "cpp",
            "h": "h",
            "hpp": "hpp",
            "cs": "csharp",
            "html": "html",
            "css": "css",
            "scss": "sass",
            "sh": "console",
            "bat": "console",
            "txt": "document",
            "pdf": "pdf",
            "zip": "zip",
            "7z": "zip",
            "tar": "zip",
            "gz": "zip",
            "xml": "xml",
            "yaml": "yaml",
            "yml": "yaml",
            "dockerfile": "docker",
            "vb": "visualstudio",
            "sql": "database"
        }

        icon_name = mappings.get(ext, ext) # Default to extension name
        
        # Search in file icons
        for svg_path in self.file_icons_all:
            # Check exact match or standard name match
            if svg_path.stem == icon_name:
                self.select_icon(svg_path)
                # Also scroll to or highlight? 
                # For now just selecting it is enough for the logic.
                # We update the search to show it? That might be nice.
                self.search_var.set(icon_name) # This will trigger filter and show only this icon
                return

    def select_icon(self, svg_path):
        self.selected_icon_path = svg_path
        self.status_label.configure(text=f"Selected Icon: {svg_path.stem}")
        self.check_ready()

    def check_ready(self):
        if self.selected_target and self.selected_icon_path:
            self.btn_apply.configure(state="normal")

    def apply_icon(self):
        self._apply_or_reset(reset=False)

    def reset_icon(self):
        self._apply_or_reset(reset=True)

    def _apply_or_reset(self, reset=False):
        if not self.selected_target:
            return

        if not reset and not self.selected_icon_path:
            return

        action = "Resetting" if reset else "Applying"
        self.status_label.configure(text=f"{action}...")

        # Run in thread
        threading.Thread(target=self._process_gio_thread, args=(reset,), daemon=True).start()

    def _process_gio_thread(self, reset):
        try:
            cmd = []
            if reset:
                cmd = ["gio", "set", "-d", str(self.selected_target), "metadata::custom-icon"]
            else:
                # Convert first
                png_path = CONVERTED_DIR / f"{self.selected_icon_path.stem}.png"
                if not png_path.exists():
                    cairosvg.svg2png(url=str(self.selected_icon_path), write_to=str(png_path), output_width=256, output_height=256)
                
                cmd = [
                    "gio", "set", "-t", "string",
                    str(self.selected_target),
                    "metadata::custom-icon",
                    f"file://{png_path}"
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                msg = "Icon reset successfully." if reset else "Icon applied successfully!"
                # Force Nautilus refresh if possible (touch the file)
                try:
                    os.utime(self.selected_target, None)
                except:
                    pass
            else:
                msg = f"Error: {result.stderr}"
            
            self.after(0, lambda: self.status_label.configure(text=msg))
            
            # If reset, clear selection state visually
            if reset:
                self.after(0, lambda: self.btn_apply.configure(state="disabled"))

        except Exception as e:
            self.after(0, lambda: self.status_label.configure(text=f"Error: {e}"))

if __name__ == "__main__":
    app = IconChangerApp()
    app.mainloop()
