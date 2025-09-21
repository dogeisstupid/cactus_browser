import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, scrolledtext, filedialog
import webview
import threading
import os
import requests
from urllib.parse import urlparse, quote
from PIL import Image, ImageTk
import json
import tempfile

class CactusBrowser:
    def __init__(self, root):
        self.root = root
        self.root.title("CactusBrowser")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # Configuration
        self.config_file = "cactus_config.json"
        self.current_theme = "Default"
        self.download_folder = os.path.join(os.path.expanduser("~"), "CactusDownloads")
        self.history = []
        self.bookmarks = []
        
        # Create download folder if it doesn't exist
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)
        
        # Load configuration
        self.load_config()
        
        # Create UI
        self.create_ui()
        
        # Initialize webview in a thread
        self.init_webview()
    
    def load_config(self):
        """Load browser configuration"""
        default_config = {
            "theme": "Default",
            "homepage": "https://www.google.com",
            "download_path": self.download_folder,
            "bookmarks": [],
            "history": []
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.current_theme = config.get("theme", "Default")
                    self.homepage = config.get("homepage", "https://www.google.com")
                    self.download_folder = config.get("download_path", self.download_folder)
                    self.bookmarks = config.get("bookmarks", [])
                    self.history = config.get("history", [])
        except:
            # Use defaults if config file is corrupted
            self.current_theme = "Default"
            self.homepage = "https://www.google.com"
            self.bookmarks = []
            self.history = []
    
    def save_config(self):
        """Save browser configuration"""
        config = {
            "theme": self.current_theme,
            "homepage": self.homepage,
            "download_path": self.download_folder,
            "bookmarks": self.bookmarks,
            "history": self.history[-100:]  # Keep only last 100 history items
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def create_ui(self):
        """Create the browser user interface"""
        # Create main frames
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create address bar
        self.create_address_bar()
        
        # Create tabs
        self.create_tab_system()
        
        # Create status bar
        self.create_status_bar()
        
        # Create side panel for bookmarks and downloads
        self.create_side_panel()
        
        # Apply initial theme
        self.apply_theme(self.current_theme)
    
    def create_address_bar(self):
        """Create the address bar with navigation buttons"""
        address_frame = ttk.Frame(self.main_frame)
        address_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Navigation buttons
        back_btn = ttk.Button(address_frame, text="◀", width=3, command=self.go_back)
        back_btn.pack(side=tk.LEFT, padx=2)
        
        forward_btn = ttk.Button(address_frame, text="▶", width=3, command=self.go_forward)
        forward_btn.pack(side=tk.LEFT, padx=2)
        
        refresh_btn = ttk.Button(address_frame, text="↻", width=3, command=self.refresh_page)
        refresh_btn.pack(side=tk.LEFT, padx=2)
        
        home_btn = ttk.Button(address_frame, text="⌂", width=3, command=self.go_home)
        home_btn.pack(side=tk.LEFT, padx=2)
        
        # Address entry
        self.address_var = tk.StringVar()
        self.address_entry = ttk.Entry(address_frame, textvariable=self.address_var)
        self.address_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.address_entry.bind("<Return>", self.navigate_to_url)
        
        # Go button
        go_btn = ttk.Button(address_frame, text="Go", command=self.navigate)
        go_btn.pack(side=tk.LEFT, padx=2)
        
        # Theme button
        theme_btn = ttk.Button(address_frame, text="🎨", command=self.show_theme_menu)
        theme_btn.pack(side=tk.LEFT, padx=2)
        
        # Bookmarks button
        bookmark_btn = ttk.Button(address_frame, text="⭐", command=self.toggle_bookmarks)
        bookmark_btn.pack(side=tk.LEFT, padx=2)
        
        # Downloads button
        download_btn = ttk.Button(address_frame, text="📥", command=self.toggle_downloads)
        download_btn.pack(side=tk.LEFT, padx=2)
    
    def create_tab_system(self):
        """Create the tab system for multiple pages"""
        # Tab control
        self.tab_control = ttk.Notebook(self.main_frame)
        self.tab_control.pack(fill=tk.BOTH, expand=True)
        
        # Add first tab
        self.add_new_tab("New Tab", "https://www.google.com")
        
        # Bind tab events
        self.tab_control.bind("<ButtonPress-1>", self.on_tab_click)
        self.tab_control.bind("<ButtonRelease-1>", self.on_tab_release)
        
        # Add "+" button for new tabs
        self.add_tab_button = ttk.Button(self.tab_control, text="+", width=2, command=self.add_new_tab)
        self.tab_control.add(self.add_tab_button, text="+")
    
    def create_status_bar(self):
        """Create the status bar at the bottom"""
        self.status_frame = ttk.Frame(self.main_frame)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(self.status_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X)
    
    def create_side_panel(self):
        """Create the side panel for bookmarks and downloads"""
        # Side panel frame (initially hidden)
        self.side_panel = ttk.Frame(self.main_frame, width=200)
        self.side_panel.pack(fill=tk.Y, side=tk.RIGHT)
        self.side_panel.pack_propagate(False)
        self.side_panel_visible = False
        
        # Panel content
        self.panel_notebook = ttk.Notebook(self.side_panel)
        self.panel_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Bookmarks tab
        self.bookmarks_frame = ttk.Frame(self.panel_notebook)
        self.panel_notebook.add(self.bookmarks_frame, text="Bookmarks")
        self.setup_bookmarks_tab()
        
        # Downloads tab
        self.downloads_frame = ttk.Frame(self.panel_notebook)
        self.panel_notebook.add(self.downloads_frame, text="Downloads")
        self.setup_downloads_tab()
        
        # History tab
        self.history_frame = ttk.Frame(self.panel_notebook)
        self.panel_notebook.add(self.history_frame, text="History")
        self.setup_history_tab()
        
        # Initially hide the side panel
        self.side_panel.pack_forget()
    
    def setup_bookmarks_tab(self):
        """Setup the bookmarks tab content"""
        # Add bookmark button
        add_btn = ttk.Button(self.bookmarks_frame, text="Add Current Page", command=self.add_current_bookmark)
        add_btn.pack(pady=5)
        
        # Bookmarks list
        bookmarks_list_frame = ttk.Frame(self.bookmarks_frame)
        bookmarks_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.bookmarks_listbox = tk.Listbox(bookmarks_list_frame)
        self.bookmarks_listbox.pack(fill=tk.BOTH, expand=True)
        self.bookmarks_listbox.bind("<Double-Button-1>", self.on_bookmark_select)
        
        # Refresh bookmarks list
        self.refresh_bookmarks_list()
    
    def setup_downloads_tab(self):
        """Setup the downloads tab content"""
        # Download path frame
        path_frame = ttk.Frame(self.downloads_frame)
        path_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(path_frame, text="Download Path:").pack(side=tk.LEFT)
        
        self.download_path_var = tk.StringVar(value=self.download_folder)
        path_entry = ttk.Entry(path_frame, textvariable=self.download_path_var, state="readonly")
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        change_btn = ttk.Button(path_frame, text="Change", command=self.change_download_path)
        change_btn.pack(side=tk.RIGHT)
        
        # Downloads list
        downloads_list_frame = ttk.Frame(self.downloads_frame)
        downloads_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a treeview for downloads
        columns = ("filename", "size", "status", "date")
        self.downloads_tree = ttk.Treeview(downloads_list_frame, columns=columns, show="headings")
        
        # Define headings
        self.downloads_tree.heading("filename", text="Filename")
        self.downloads_tree.heading("size", text="Size")
        self.downloads_tree.heading("status", text="Status")
        self.downloads_tree.heading("date", text="Date")
        
        # Define columns
        self.downloads_tree.column("filename", width=200)
        self.downloads_tree.column("size", width=80)
        self.downloads_tree.column("status", width=100)
        self.downloads_tree.column("date", width=120)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(downloads_list_frame, orient=tk.VERTICAL, command=self.downloads_tree.yview)
        self.downloads_tree.configure(yscrollcommand=scrollbar.set)
        
        self.downloads_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Open folder button
        open_btn = ttk.Button(self.downloads_frame, text="Open Download Folder", command=self.open_download_folder)
        open_btn.pack(pady=5)
    
    def setup_history_tab(self):
        """Setup the history tab content"""
        # Clear history button
        clear_btn = ttk.Button(self.history_frame, text="Clear History", command=self.clear_history)
        clear_btn.pack(pady=5)
        
        # History list
        history_list_frame = ttk.Frame(self.history_frame)
        history_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.history_listbox = tk.Listbox(history_list_frame)
        self.history_listbox.pack(fill=tk.BOTH, expand=True)
        self.history_listbox.bind("<Double-Button-1>", self.on_history_select)
        
        # Refresh history list
        self.refresh_history_list()
    
    def init_webview(self):
        """Initialize the webview component"""
        # This will be implemented in the actual webview integration
        pass
    
    def add_new_tab(self, title="New Tab", url=None):
        """Add a new browser tab"""
        if url is None:
            url = self.homepage
        
        # Create a frame for the new tab
        tab_frame = ttk.Frame(self.tab_control)
        
        # Add webview to the tab (this would be the actual webview component)
        # For demonstration, we'll add a placeholder
        webview_placeholder = tk.Label(tab_frame, text=f"WebView would display: {url}", 
                                      bg="white", relief=tk.SUNKEN)
        webview_placeholder.pack(fill=tk.BOTH, expand=True)
        
        # Add the tab
        self.tab_control.insert(self.tab_control.index(tk.END) - 1, tab_frame, text=title)
        self.tab_control.select(tab_frame)
        
        # Update address bar
        self.address_var.set(url)
        
        # Add to history
        self.add_to_history(url, title)
    
    def on_tab_click(self, event):
        """Handle tab click events"""
        if self.tab_control.index("@%d,%d" % (event.x, event.y)) == self.tab_control.index(tk.END) - 1:
            # Clicked on the "+" button
            self.add_new_tab()
    
    def on_tab_release(self, event):
        """Handle tab release events"""
        pass
    
    def navigate_to_url(self, event=None):
        """Navigate to the URL in the address bar"""
        self.navigate()
    
    def navigate(self):
        """Navigate to the URL in the address bar"""
        url = self.address_var.get().strip()
        
        if not url:
            return
        
        # Add http:// if no protocol specified
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Get current tab
        current_tab = self.tab_control.select()
        if current_tab:
            tab_index = self.tab_control.index(current_tab)
            # Update the webview in the current tab (placeholder for demonstration)
            for child in self.tab_control.winfo_children()[tab_index].winfo_children():
                if isinstance(child, tk.Label):
                    child.config(text=f"WebView would display: {url}")
            
            # Update tab title
            self.tab_control.tab(tab_index, text=url[:20] + '...' if len(url) > 20 else url)
            
            # Add to history
            self.add_to_history(url, url)
    
    def go_back(self):
        """Navigate back in history"""
        # Placeholder for back navigation
        self.status_label.config(text="Back button pressed")
    
    def go_forward(self):
        """Navigate forward in history"""
        # Placeholder for forward navigation
        self.status_label.config(text="Forward button pressed")
    
    def refresh_page(self):
        """Refresh the current page"""
        # Placeholder for refresh
        self.status_label.config(text="Page refreshed")
    
    def go_home(self):
        """Navigate to the homepage"""
        self.address_var.set(self.homepage)
        self.navigate()
    
    def show_theme_menu(self):
        """Show the theme selection menu"""
        theme_window = tk.Toplevel(self.root)
        theme_window.title("Select Theme")
        theme_window.geometry("400x500")
        theme_window.resizable(False, False)
        
        # Create a canvas with scrollbar for the theme grid
        canvas = tk.Canvas(theme_window)
        scrollbar = ttk.Scrollbar(theme_window, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Define 55+ color themes
        themes = [
            # Default themes
            ("Default", "#ffffff", "#000000"),
            ("Dark", "#2c2c2c", "#ffffff"),
            ("Blue", "#3498db", "#ffffff"),
            ("Green", "#2ecc71", "#ffffff"),
            ("Red", "#e74c3c", "#ffffff"),
            ("Purple", "#9b59b6", "#ffffff"),
            ("Orange", "#e67e22", "#ffffff"),
            
            # Additional color themes
            ("Midnight Blue", "#2c3e50", "#ecf0f1"),
            ("Wet Asphalt", "#34495e", "#ecf0f1"),
            ("Sun Flower", "#f1c40f", "#2c3e50"),
            ("Carrot", "#e67e22", "#2c3e50"),
            ("Alizarin", "#e74c3c", "#2c3e50"),
            ("Clouds", "#ecf0f1", "#2c3e50"),
            ("Concrete", "#95a5a6", "#2c3e50"),
            ("Pink", "#ff6b81", "#2c3e50"),
            ("Teal", "#008080", "#ffffff"),
            ("Navy", "#000080", "#ffffff"),
            ("Maroon", "#800000", "#ffffff"),
            ("Olive", "#808000", "#ffffff"),
            ("Lime", "#00ff00", "#000000"),
            ("Aqua", "#00ffff", "#000000"),
            ("Fuchsia", "#ff00ff", "#000000"),
            ("Silver", "#c0c0c0", "#000000"),
            ("Gray", "#808080", "#ffffff"),
            ("Black", "#000000", "#ffffff"),
            ("White", "#ffffff", "#000000"),
            
            # More vibrant themes
            ("Electric Blue", "#7efff5", "#000000"),
            ("Neon Green", "#39ff14", "#000000"),
            ("Hot Pink", "#ff69b4", "#000000"),
            ("Bright Orange", "#ff6700", "#000000"),
            ("Lemon Yellow", "#fff44f", "#000000"),
            ("Lavender", "#e6e6fa", "#000000"),
            ("Mint", "#98ff98", "#000000"),
            ("Coral", "#ff7f50", "#000000"),
            ("Gold", "#ffd700", "#000000"),
            ("Sky Blue", "#87ceeb", "#000000"),
            ("Salmon", "#fa8072", "#000000"),
            ("Khaki", "#f0e68c", "#000000"),
            ("Plum", "#dda0dd", "#000000"),
            ("Cyan", "#00ffff", "#000000"),
            ("Magenta", "#ff00ff", "#000000"),
            ("Spring Green", "#00ff7f", "#000000"),
            ("Tomato", "#ff6347", "#000000"),
            ("Slate Blue", "#6a5acd", "#ffffff"),
            ("Forest Green", "#228b22", "#ffffff"),
            ("Royal Blue", "#4169e1", "#ffffff"),
            ("Crimson", "#dc143c", "#ffffff"),
            ("Dark Orchid", "#9932cc", "#ffffff"),
            ("Sienna", "#a0522d", "#ffffff"),
            ("Steel Blue", "#4682b4", "#ffffff"),
            ("Peru", "#cd853f", "#ffffff"),
            ("Dark Cyan", "#008b8b", "#ffffff"),
            ("Indigo", "#4b0082", "#ffffff"),
            ("Dark Magenta", "#8b008b", "#ffffff"),
            ("Dark Red", "#8b0000", "#ffffff"),
            ("Dark Green", "#006400", "#ffffff"),
            ("Dark Blue", "#00008b", "#ffffff"),
            ("Dark Violet", "#9400d3", "#ffffff")
        ]
        
        # Create theme buttons
        rows, cols = 10, 5
        for i, (name, bg_color, fg_color) in enumerate(themes):
            row, col = i // cols, i % cols
            btn = tk.Button(
                scrollable_frame, 
                text=name, 
                bg=bg_color, 
                fg=fg_color,
                width=15,
                height=2,
                command=lambda n=name, bg=bg_color, fg=fg_color: self.select_theme(n, bg, fg, theme_window)
            )
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
        
        # Configure grid weights
        for i in range(cols):
            scrollable_frame.columnconfigure(i, weight=1)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def select_theme(self, name, bg_color, fg_color, theme_window):
        """Select a theme and apply it"""
        self.current_theme = name
        self.apply_theme(name)
        theme_window.destroy()
        self.save_config()
    
    def apply_theme(self, theme_name):
        """Apply the selected theme to the browser"""
        # This is a simplified theme application
        # In a real implementation, you would configure all widget colors
        
        # Define some theme colors based on theme name
        theme_colors = {
            "Default": {"bg": "white", "fg": "black"},
            "Dark": {"bg": "#2c2c2c", "fg": "white"},
            "Blue": {"bg": "#3498db", "fg": "white"},
            "Green": {"bg": "#2ecc71", "fg": "white"},
            "Red": {"bg": "#e74c3c", "fg": "white"},
            "Purple": {"bg": "#9b59b6", "fg": "white"},
            "Orange": {"bg": "#e67e22", "fg": "white"},
        }
        
        # Get colors for the current theme or use defaults
        colors = theme_colors.get(theme_name, theme_colors["Default"])
        
        # Apply colors to some elements (simplified)
        try:
            self.root.configure(bg=colors["bg"])
            self.status_label.configure(background=colors["bg"], foreground=colors["fg"])
        except:
            pass
    
    def toggle_bookmarks(self):
        """Toggle bookmarks panel visibility"""
        if self.side_panel_visible:
            self.side_panel.pack_forget()
            self.side_panel_visible = False
        else:
            self.side_panel.pack(fill=tk.Y, side=tk.RIGHT)
            self.side_panel_visible = True
            self.panel_notebook.select(0)  # Show bookmarks tab
            self.refresh_bookmarks_list()
    
    def toggle_downloads(self):
        """Toggle downloads panel visibility"""
        if self.side_panel_visible:
            self.side_panel.pack_forget()
            self.side_panel_visible = False
        else:
            self.side_panel.pack(fill=tk.Y, side=tk.RIGHT)
            self.side_panel_visible = True
            self.panel_notebook.select(1)  # Show downloads tab
    
    def add_current_bookmark(self):
        """Add current page to bookmarks"""
        url = self.address_var.get()
        title = self.tab_control.tab(self.tab_control.select(), "text")
        
        if url and url != "about:blank":
            self.bookmarks.append({"title": title, "url": url})
            self.save_config()
            self.refresh_bookmarks_list()
            messagebox.showinfo("Bookmark Added", f"Added '{title}' to bookmarks")
    
    def refresh_bookmarks_list(self):
        """Refresh the bookmarks listbox"""
        self.bookmarks_listbox.delete(0, tk.END)
        for bookmark in self.bookmarks:
            self.bookmarks_listbox.insert(tk.END, f"{bookmark['title']} - {bookmark['url']}")
    
    def on_bookmark_select(self, event):
        """Handle bookmark selection"""
        selection = self.bookmarks_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.bookmarks):
                url = self.bookmarks[index]["url"]
                self.address_var.set(url)
                self.navigate()
    
    def change_download_path(self):
        """Change the download folder path"""
        folder = filedialog.askdirectory(initialdir=self.download_folder)
        if folder:
            self.download_folder = folder
            self.download_path_var.set(folder)
            self.save_config()
    
    def open_download_folder(self):
        """Open the download folder in file explorer"""
        os.startfile(self.download_folder)  # Works on Windows
    
    def add_to_history(self, url, title):
        """Add a URL to history"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.history.append({"url": url, "title": title, "timestamp": timestamp})
        self.save_config()
        self.refresh_history_list()
    
    def refresh_history_list(self):
        """Refresh the history listbox"""
        self.history_listbox.delete(0, tk.END)
        for item in self.history[-50:]:  # Show last 50 items
            self.history_listbox.insert(tk.END, f"{item['timestamp']} - {item['title']}")
    
    def on_history_select(self, event):
        """Handle history item selection"""
        selection = self.history_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.history):
                url = self.history[index]["url"]
                self.address_var.set(url)
                self.navigate()
    
    def clear_history(self):
        """Clear browsing history"""
        if messagebox.askyesno("Clear History", "Are you sure you want to clear all history?"):
            self.history = []
            self.save_config()
            self.refresh_history_list()

# Run the browser
if __name__ == "__main__":
    root = tk.Tk()
    browser = CactusBrowser(root)
    root.mainloop()