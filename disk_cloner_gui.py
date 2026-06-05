#!/usr/bin/env python3
"""
Windows Disk Cloner GUI - Inspired by Clonezilla
Graphical interface for the disk cloning utility

Author: Custom Build
License: GPL
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import sys
from disk_cloner import DiskCloner


class DiskClonerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Windows Disk Cloner - Inspired by Clonezilla")
        self.root.geometry("850x650")
        self.root.minsize(750, 550)

        self.cloner = DiskCloner()
        self.disks = []
        self.is_cloning = False
        self.progress_style = None

        # Override log method to redirect to GUI
        self.original_log = self.cloner.log
        self.cloner.log = self.gui_log

        # Configure progress bar styles first (before creating widgets)
        self.setup_progress_styles()
        
        self.create_widgets()
        
        # Center the window on screen (after widgets are created)
        self.center_window()
        
        self.check_admin()
        self.refresh_disks()

    def create_widgets(self):
        """Create GUI widgets with dynamic grid layout"""
        # Configure root grid weights for dynamic resizing
        self.root.grid_rowconfigure(1, weight=1)  # Notebook row
        self.root.grid_rowconfigure(2, weight=0)  # Log row (fixed)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Title (compact, no expansion)
        title_frame = ttk.Frame(self.root, padding="3")
        title_frame.grid(row=0, column=0, sticky="ew", padx=2, pady=1)
        title_frame.grid_columnconfigure(0, weight=1)

        title_label = ttk.Label(
            title_frame,
            text="Windows Disk Cloner",
            font=("Arial", 12, "bold")
        )
        title_label.grid(row=0, column=0, pady=1)

        subtitle_label = ttk.Label(
            title_frame,
            text="Based on Clonezilla methodology with Windows-native tools",
            font=("Arial", 7, "italic")
        )
        subtitle_label.grid(row=1, column=0, pady=0)

        # Notebook for tabs (expandable)
        notebook = ttk.Notebook(self.root)
        notebook.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)

        # Tab 1: Drive to Image
        self.tab_drive_to_image = ttk.Frame(notebook)
        notebook.add(self.tab_drive_to_image, text="Clone Drive to Image")
        self.create_drive_to_image_tab()

        # Tab 2: Disk to Disk
        self.tab_disk_to_disk = ttk.Frame(notebook)
        notebook.add(self.tab_disk_to_disk, text="Clone Disk to Disk")
        self.create_disk_to_disk_tab()

        # Tab 3: Disk Info
        self.tab_disk_info = ttk.Frame(notebook)
        notebook.add(self.tab_disk_info, text="Disk Information")
        self.create_disk_info_tab()

        # Log panel at bottom (fixed height, scrollable)
        log_frame = ttk.LabelFrame(self.root, text="Activity Log", padding="3")
        log_frame.grid(row=2, column=0, sticky="ew", padx=2, pady=2)
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=6,
            state=tk.DISABLED,
            wrap=tk.WORD,
            font=("Consolas", 7)
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")

        # Status bar (fixed at bottom)
        self.status_bar = ttk.Label(
            self.root,
            text="Ready",
            relief=tk.SUNKEN,
            anchor=tk.W,
            font=("Arial", 8)
        )
        self.status_bar.grid(row=3, column=0, sticky="ew")

    def center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def setup_progress_styles(self):
        """Setup progress bar styles for different states"""
        style = ttk.Style()
        
        try:
            # Map the styles to ensure they exist
            # Running state (bright blue)
            try:
                style.map("Horizontal.Running.TProgressbar",
                         background=[('active', '#00a4ef'), ('!active', '#00a4ef')])
                style.configure("Horizontal.Running.TProgressbar", 
                               background='#00a4ef', 
                               troughcolor='#e1e1e1')
            except:
                # If mapping fails, try simple configuration
                try:
                    style.configure("Horizontal.Running.TProgressbar", background='#00a4ef')
                except:
                    pass
            
            # Error/stopped state (red) - most important for user feedback
            try:
                style.map("Horizontal.Error.TProgressbar",
                         background=[('active', '#d13438'), ('!active', '#d13438')])
                style.configure("Horizontal.Error.TProgressbar", 
                               background='#d13438', 
                               troughcolor='#e1e1e1')
            except:
                try:
                    style.configure("Horizontal.Error.TProgressbar", background='red')
                except:
                    pass
            
            # Success state (green)
            try:
                style.map("Horizontal.Success.TProgressbar",
                         background=[('active', '#107c10'), ('!active', '#107c10')])
                style.configure("Horizontal.Success.TProgressbar", 
                               background='#107c10', 
                               troughcolor='#e1e1e1')
            except:
                try:
                    style.configure("Horizontal.Success.TProgressbar", background='green')
                except:
                    pass
        except Exception as e:
            # If style configuration fails completely, styles will use defaults
            pass

    def set_progress_running(self, progress_bar):
        """Set progress bar to running state"""
        try:
            # Try the full style name first
            progress_bar.configure(style="Horizontal.Running.TProgressbar")
        except:
            try:
                # Fallback to shorter name
                progress_bar.configure(style="Running.TProgressbar")
            except:
                # If all else fails, just use default (progress will still work)
                try:
                    progress_bar.configure(style="TProgressbar")
                except:
                    pass

    def set_progress_error(self, progress_bar):
        """Set progress bar to error/stopped state (red)"""
        try:
            progress_bar.configure(style="Horizontal.Error.TProgressbar")
        except:
            try:
                progress_bar.configure(style="Error.TProgressbar")
            except:
                # If style fails, at least keep the progress bar functional
                try:
                    progress_bar.configure(style="TProgressbar")
                except:
                    pass

    def set_progress_success(self, progress_bar):
        """Set progress bar to success state (green)"""
        try:
            progress_bar.configure(style="Horizontal.Success.TProgressbar")
        except:
            try:
                progress_bar.configure(style="Success.TProgressbar")
            except:
                try:
                    progress_bar.configure(style="TProgressbar")
                except:
                    pass

    def set_progress_ready(self, progress_bar):
        """Set progress bar to ready state (default)"""
        try:
            progress_bar.configure(style="TProgressbar")
        except:
            pass  # Use default style

    def create_drive_to_image_tab(self):
        """Create Drive to Image tab with scrollable content"""
        # Create scrollable frame
        canvas = tk.Canvas(self.tab_drive_to_image, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.tab_drive_to_image, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Use grid for proper layout
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tab_drive_to_image.grid_rowconfigure(0, weight=1)
        self.tab_drive_to_image.grid_columnconfigure(0, weight=1)

        frame = ttk.Frame(scrollable_frame, padding="5")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Update canvas width when frame changes
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Make canvas width match scrollable_frame width
            canvas_width = event.width
            canvas.itemconfig(canvas.find_all()[0], width=canvas_width)
        
        scrollable_frame.bind('<Configure>', configure_scroll_region)

        # Instructions (more compact)
        instructions = ttk.Label(
            frame,
            text="Clone a Windows drive (partition) to an image backup file.\n"
                 "This creates a complete backup of the selected drive.",
            justify=tk.LEFT,
            wraplength=600,
            font=("Arial", 8)
        )
        instructions.pack(pady=3)

        # Source drive selection (more compact)
        source_frame = ttk.LabelFrame(frame, text="Source Drive", padding="4")
        source_frame.pack(fill=tk.X, pady=2)

        ttk.Label(source_frame, text="Select drive to backup:").pack(anchor=tk.W)

        self.drive_var = tk.StringVar()
        self.drive_combo = ttk.Combobox(
            source_frame,
            textvariable=self.drive_var,
            state="readonly",
            width=50
        )
        self.drive_combo.pack(fill=tk.X, pady=5)

        refresh_btn = ttk.Button(
            source_frame,
            text="Refresh Drives",
            command=self.refresh_drives
        )
        refresh_btn.pack(anchor=tk.W)

        # Output directory (more compact)
        output_frame = ttk.LabelFrame(frame, text="Output Location", padding="4")
        output_frame.pack(fill=tk.X, pady=2)

        ttk.Label(output_frame, text="Backup destination folder:").pack(anchor=tk.W)

        output_entry_frame = ttk.Frame(output_frame)
        output_entry_frame.pack(fill=tk.X, pady=5)

        self.output_var = tk.StringVar(value="E:\\DiskBackups")
        output_entry = ttk.Entry(
            output_entry_frame,
            textvariable=self.output_var,
            width=60
        )
        output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        browse_btn = ttk.Button(
            output_entry_frame,
            text="Browse...",
            command=self.browse_output
        )
        browse_btn.pack(side=tk.LEFT, padx=5)

        # Options (more compact)
        options_frame = ttk.LabelFrame(frame, text="Options", padding="4")
        options_frame.pack(fill=tk.X, pady=2)

        self.gen_checksum_var = tk.BooleanVar(value=True)
        checksum_check = ttk.Checkbutton(
            options_frame,
            text="Generate MD5 checksums (recommended)",
            variable=self.gen_checksum_var
        )
        checksum_check.pack(anchor=tk.W)

        self.verify_var = tk.BooleanVar(value=True)
        verify_check = ttk.Checkbutton(
            options_frame,
            text="Verify backup after completion",
            variable=self.verify_var
        )
        verify_check.pack(anchor=tk.W)

        # Clone button
        self.clone_drive_btn = ttk.Button(
            frame,
            text="Start Backup",
            command=self.start_drive_clone,
            style="Accent.TButton"
        )
        self.clone_drive_btn.pack(pady=8)

        # Progress frame (compact)
        progress_frame = ttk.LabelFrame(frame, text="Progress", padding="5")
        progress_frame.pack(fill=tk.X, pady=3)

        # Progress bar (determinate mode)
        self.drive_progress = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            maximum=100,
            length=350,
            style="TProgressbar"
        )
        self.drive_progress.pack(fill=tk.X, pady=2)

        # Progress label
        self.drive_progress_label = ttk.Label(
            progress_frame,
            text="Ready",
            font=("Arial", 8)
        )
        self.drive_progress_label.pack(pady=1)

    def create_disk_to_disk_tab(self):
        """Create Disk to Disk tab with scrollable content"""
        # Create scrollable frame
        canvas = tk.Canvas(self.tab_disk_to_disk, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.tab_disk_to_disk, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Use grid for proper layout
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tab_disk_to_disk.grid_rowconfigure(0, weight=1)
        self.tab_disk_to_disk.grid_columnconfigure(0, weight=1)

        frame = ttk.Frame(scrollable_frame, padding="5")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Update canvas width when frame changes
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Make canvas width match scrollable_frame width
            canvas_width = event.width
            canvas.itemconfig(canvas.find_all()[0], width=canvas_width)
        
        scrollable_frame.bind('<Configure>', configure_scroll_region)

        # Warning (more compact)
        warning = ttk.Label(
            frame,
            text="⚠ WARNING: This will completely erase the target disk!\n"
                 "Use this to clone one entire physical disk to another.",
            justify=tk.CENTER,
            foreground="red",
            font=("Arial", 8, "bold")
        )
        warning.pack(pady=3)

        # Source disk (more compact)
        source_frame = ttk.LabelFrame(frame, text="Source Disk", padding="4")
        source_frame.pack(fill=tk.X, pady=2)

        ttk.Label(source_frame, text="Disk to clone FROM:").pack(anchor=tk.W)

        self.source_disk_var = tk.StringVar()
        self.source_disk_combo = ttk.Combobox(
            source_frame,
            textvariable=self.source_disk_var,
            state="readonly",
            width=70
        )
        self.source_disk_combo.pack(fill=tk.X, pady=5)

        # Target disk (more compact)
        target_frame = ttk.LabelFrame(frame, text="Target Disk", padding="4")
        target_frame.pack(fill=tk.X, pady=2)

        ttk.Label(target_frame, text="Disk to clone TO (will be ERASED):").pack(anchor=tk.W)

        self.target_disk_var = tk.StringVar()
        self.target_disk_combo = ttk.Combobox(
            target_frame,
            textvariable=self.target_disk_var,
            state="readonly",
            width=70
        )
        self.target_disk_combo.pack(fill=tk.X, pady=5)

        refresh_disks_btn = ttk.Button(
            frame,
            text="Refresh Disk List",
            command=self.refresh_disks
        )
        refresh_disks_btn.pack(pady=5)

        # Clone mode options (more compact)
        mode_frame = ttk.LabelFrame(frame, text="Clone Mode", padding="4")
        mode_frame.pack(fill=tk.X, pady=2)

        self.raw_mode_var = tk.BooleanVar(value=True)  # Default to RAW mode for complete OS disk clones
        raw_mode_check = ttk.Checkbutton(
            mode_frame,
            text="Use RAW mode (sector-by-sector copy)",
            variable=self.raw_mode_var
        )
        raw_mode_check.pack(anchor=tk.W)

        ttk.Label(
            mode_frame,
            text="RAW mode (default/recommended for C: OS clones): sector-by-sector, most complete.\n"
                 "Best from Windows Recovery/USB so the source and target are not actively in use.\n"
                 "Unchecked fallback: robocopy file-level copy; less exact for a live OS disk.",
            foreground="gray",
            font=("Arial", 8)
        ).pack(anchor=tk.W, pady=2)

        # Partition resize option (more compact)
        resize_frame = ttk.LabelFrame(frame, text="Post-Clone Options", padding="4")
        resize_frame.pack(fill=tk.X, pady=2)

        self.resize_partition_var = tk.BooleanVar(value=False)
        resize_check = ttk.Checkbutton(
            resize_frame,
            text="Resize last partition to fill all available disk space after cloning",
            variable=self.resize_partition_var
        )
        resize_check.pack(anchor=tk.W)

        ttk.Label(
            resize_frame,
            text="This will extend the last data partition to utilize all available storage on the target disk.\n"
                 "Useful when the target disk is larger than the source disk.",
            foreground="gray",
            font=("Arial", 8)
        ).pack(anchor=tk.W, pady=2)

        # Clone button
        self.clone_disk_btn = ttk.Button(
            frame,
            text="Start Disk Clone",
            command=self.start_disk_clone,
            style="Accent.TButton"
        )
        self.clone_disk_btn.pack(pady=8)

        # Progress frame (compact)
        progress_frame = ttk.LabelFrame(frame, text="Progress", padding="5")
        progress_frame.pack(fill=tk.X, pady=3)

        # Progress bar (determinate mode)
        self.disk_progress = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            maximum=100,
            length=350,
            style="TProgressbar"
        )
        self.disk_progress.pack(fill=tk.X, pady=2)

        # Progress label
        self.disk_progress_label = ttk.Label(
            progress_frame,
            text="Ready",
            font=("Arial", 8)
        )
        self.disk_progress_label.pack(pady=1)

    def create_disk_info_tab(self):
        """Create Disk Information tab with scrollable content"""
        # Create scrollable frame
        canvas = tk.Canvas(self.tab_disk_info, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.tab_disk_info, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Use grid for proper layout
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tab_disk_info.grid_rowconfigure(0, weight=1)
        self.tab_disk_info.grid_columnconfigure(0, weight=1)

        frame = ttk.Frame(scrollable_frame, padding="5")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Update canvas width when frame changes
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas_width = event.width
            canvas.itemconfig(canvas.find_all()[0], width=canvas_width)
        
        scrollable_frame.bind('<Configure>', configure_scroll_region)

        ttk.Label(
            frame,
            text="Detected Physical Disks and Partitions",
            font=("Arial", 10, "bold")
        ).pack(pady=5)

        # Treeview for disk info
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.disk_tree = ttk.Treeview(
            tree_frame,
            columns=("Type", "Size", "Status", "Details"),
            yscrollcommand=scrollbar.set
        )
        self.disk_tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.disk_tree.yview)

        self.disk_tree.heading("#0", text="Device")
        self.disk_tree.heading("Type", text="Type")
        self.disk_tree.heading("Size", text="Size (GB)")
        self.disk_tree.heading("Status", text="Status")
        self.disk_tree.heading("Details", text="Details")

        self.disk_tree.column("#0", width=150)
        self.disk_tree.column("Type", width=80)
        self.disk_tree.column("Size", width=80)
        self.disk_tree.column("Status", width=80)
        self.disk_tree.column("Details", width=250)

        refresh_info_btn = ttk.Button(
            frame,
            text="Refresh Information",
            command=self.refresh_disk_info
        )
        refresh_info_btn.pack(pady=5)

    def check_admin(self):
        """Check and warn if not running as admin"""
        if not self.cloner.is_admin:
            messagebox.showwarning(
                "Administrator Required",
                "This application requires administrator privileges.\n\n"
                "Please run as Administrator for full functionality."
            )
            self.status_bar.config(text="⚠ Not running as Administrator - limited functionality")

    def gui_log(self, message, level="INFO"):
        """Log to GUI instead of console"""
        self.original_log(message, level)

        # Update log text widget
        self.log_text.config(state=tk.NORMAL)
        timestamp = message.split(']')[0].replace('[', '')
        log_line = f"{message}\n"

        # Color coding
        if level == "ERROR":
            self.log_text.insert(tk.END, log_line, "error")
            self.log_text.tag_config("error", foreground="red")
        elif level == "SUCCESS":
            self.log_text.insert(tk.END, log_line, "success")
            self.log_text.tag_config("success", foreground="green")
        elif level == "WARNING":
            self.log_text.insert(tk.END, log_line, "warning")
            self.log_text.tag_config("warning", foreground="orange")
        else:
            self.log_text.insert(tk.END, log_line)

        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

        # Update status bar
        self.status_bar.config(text=message.split(']')[-1].strip())

    def refresh_disks(self):
        """Refresh disk list"""
        self.gui_log("Refreshing disk list...")
        self.disks = self.cloner.scan_disks()

        # Update disk to disk combos
        disk_list = []
        for disk in self.disks:
            disk_str = f"Disk {disk['index']}: {disk['model']} ({disk['size_gb']} GB)"
            disk_list.append(disk_str)

        self.source_disk_combo['values'] = disk_list
        self.target_disk_combo['values'] = disk_list

        # Refresh disk info tab
        self.refresh_disk_info()

    def refresh_drives(self):
        """Refresh drive (partition) list"""
        self.gui_log("Refreshing drive list...")

        drive_list = []
        for disk in self.cloner.scan_disks():
            partitions = self.cloner.get_disk_partitions(disk['index'])
            for part in partitions:
                if 'drive_letter' in part:
                    drive_str = (f"{part['drive_letter']} - "
                               f"{part.get('label', 'No Label')} "
                               f"({part['size_gb']} GB, {part.get('file_system', 'Unknown')})")
                    drive_list.append(drive_str)

        self.drive_combo['values'] = drive_list

    def refresh_disk_info(self):
        """Refresh disk information treeview"""
        # Clear existing items
        for item in self.disk_tree.get_children():
            self.disk_tree.delete(item)

        # Add disk info
        for disk in self.disks:
            disk_id = self.disk_tree.insert(
                "",
                tk.END,
                text=f"Disk {disk['index']}",
                values=(
                    "Physical Disk",
                    disk['size_gb'],
                    disk['status'],
                    f"{disk['model']} ({disk['interface']})"
                )
            )

            # Add partitions
            partitions = self.cloner.get_disk_partitions(disk['index'])
            for part in partitions:
                drive_letter = part.get('drive_letter', 'N/A')
                fs = part.get('file_system', 'Unknown')
                label = part.get('label', 'No Label')
                bootable = "Bootable" if part.get('bootable') else ""

                self.disk_tree.insert(
                    disk_id,
                    tk.END,
                    text=f"  Partition {part['index']}",
                    values=(
                        f"Partition ({fs})",
                        part['size_gb'],
                        bootable,
                        f"{drive_letter} - {label}"
                    )
                )

    def browse_output(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory(
            initialdir=self.output_var.get(),
            title="Select Backup Destination Folder"
        )
        if directory:
            self.output_var.set(directory)

    def start_drive_clone(self):
        """Start drive to image cloning"""
        if self.is_cloning:
            messagebox.showwarning("Busy", "A cloning operation is already in progress!")
            return

        drive_selection = self.drive_var.get()
        if not drive_selection:
            messagebox.showerror("Error", "Please select a source drive!")
            return

        output_dir = self.output_var.get()
        if not output_dir:
            messagebox.showerror("Error", "Please specify an output directory!")
            return

        # Extract drive letter
        drive_letter = drive_selection.split(' ')[0]

        # Confirm
        result = messagebox.askyesno(
            "Confirm Backup",
            f"Create backup of drive {drive_letter}?\n\n"
            f"Destination: {output_dir}\n\n"
            f"This may take a while depending on the size of the drive."
        )

        if not result:
            return

        # Capture config values BEFORE starting the thread to avoid race conditions
        # These are read from the GUI checkboxes and stored locally
        gen_checksum = self.gen_checksum_var.get()
        verify_backup = self.verify_var.get()

        # Start cloning in background thread
        self.is_cloning = True
        self.clone_drive_btn.config(state=tk.DISABLED)
        self.drive_progress['value'] = 0
        self.drive_progress_label.config(text="Starting backup...")
        self.set_progress_running(self.drive_progress)

        def clone_thread():
            try:
                # Update config at the start of the thread (thread-safe timing)
                # This ensures config is set before any cloning operations begin
                self.cloner.config['gen_md5sum'] = gen_checksum
                self.cloner.config['verify_after_clone'] = verify_backup
                
                # Override log to update progress
                original_log = self.cloner.log
                def progress_log(message, level="INFO"):
                    original_log(message, level)
                    # Keep progress bar in running state during operation
                    if "Starting" in message or "Cloning" in message or "Running" in message:
                        self.root.after(0, lambda: self.set_progress_running(self.drive_progress))
                    self.root.after(0, lambda m=message: self.drive_progress_label.config(text=m.split(']')[-1].strip()[:80]))
                
                self.cloner.log = progress_log
                
                success = self.cloner.clone_drive_to_image(drive_letter, output_dir)
                
                # Restore original log
                self.cloner.log = original_log
                if success:
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Success",
                        f"Drive {drive_letter} backed up successfully!"
                    ))
                else:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Error",
                        "Backup failed! Check the log for details."
                    ))
            finally:
                self.is_cloning = False
                self.root.after(0, lambda: self.clone_drive_btn.config(state=tk.NORMAL))
                if success:
                    self.root.after(0, lambda: self.drive_progress.config(value=100))
                    self.root.after(0, lambda: self.set_progress_success(self.drive_progress))
                    self.root.after(0, lambda: self.drive_progress_label.config(text="Completed successfully"))
                else:
                    self.root.after(0, lambda: self.drive_progress.config(value=0))
                    self.root.after(0, lambda: self.set_progress_error(self.drive_progress))
                    self.root.after(0, lambda: self.drive_progress_label.config(text="Failed - Check logs"))

        thread = threading.Thread(target=clone_thread, daemon=True)
        thread.start()

    def start_disk_clone(self):
        """Start disk to disk cloning"""
        if self.is_cloning:
            messagebox.showwarning("Busy", "A cloning operation is already in progress!")
            return

        source_selection = self.source_disk_var.get()
        target_selection = self.target_disk_var.get()

        if not source_selection or not target_selection:
            messagebox.showerror("Error", "Please select both source and target disks!")
            return

        # Extract disk indices
        source_idx = int(source_selection.split(':')[0].replace('Disk ', ''))
        target_idx = int(target_selection.split(':')[0].replace('Disk ', ''))

        if source_idx == target_idx:
            messagebox.showerror("Error", "Source and target disks must be different!")
            return

        # Strong confirmation
        result = messagebox.askyesno(
            "⚠ DESTRUCTIVE OPERATION WARNING",
            f"You are about to clone:\n\n"
            f"FROM: {source_selection}\n"
            f"TO: {target_selection}\n\n"
            f"⚠ ALL DATA ON THE TARGET DISK WILL BE PERMANENTLY ERASED!\n\n"
            f"Are you absolutely sure you want to continue?",
            icon=messagebox.WARNING
        )

        if not result:
            return

        # Second confirmation
        result2 = messagebox.askyesno(
            "Final Confirmation",
            "This is your last chance to cancel.\n\n"
            "Continue with disk cloning?",
            icon=messagebox.WARNING
        )

        if not result2:
            return

        # Capture config values BEFORE starting the thread
        use_raw_mode = self.raw_mode_var.get()
        resize_partition = self.resize_partition_var.get()

        # Start cloning
        self.is_cloning = True
        self.clone_disk_btn.config(state=tk.DISABLED)
        self.disk_progress['value'] = 0
        self.disk_progress_label.config(text="Starting clone operation...")
        self.set_progress_running(self.disk_progress)

        def clone_thread():
            try:
                # Override log to update progress
                original_log = self.cloner.log
                def progress_log(message, level="INFO"):
                    original_log(message, level)
                    # Try to parse progress from message
                    if "Progress:" in message:
                        try:
                            # Extract percentage from "Progress: X%"
                            import re
                            match = re.search(r'Progress:\s*(\d+)%', message)
                            if match:
                                percent = int(match.group(1))
                                self.root.after(0, lambda p=percent: self.disk_progress.config(value=p))
                                self.root.after(0, lambda: self.set_progress_running(self.disk_progress))
                                self.root.after(0, lambda m=message: self.disk_progress_label.config(text=m.split(']')[-1].strip()))
                        except:
                            pass
                    # Keep progress bar in running state during operation
                    if "Progress:" in message or "Starting" in message or "Opening" in message or "Copying" in message:
                        self.root.after(0, lambda: self.set_progress_running(self.disk_progress))
                    self.root.after(0, lambda m=message: self.disk_progress_label.config(text=m.split(']')[-1].strip()[:80]))
                
                self.cloner.log = progress_log
                
                success = self.cloner.clone_disk_to_disk(source_idx, target_idx, use_raw_mode=use_raw_mode, resize_partition=resize_partition)
                
                # Restore original log
                self.cloner.log = original_log
                if success:
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Success",
                        "Disk cloned successfully!\n\n"
                        "You may need to reboot and select the new disk from BIOS to boot from it."
                    ))
                else:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Error",
                        "Disk cloning failed! Check the log for details."
                    ))
            finally:
                self.is_cloning = False
                self.root.after(0, lambda: self.clone_disk_btn.config(state=tk.NORMAL))
                if success:
                    self.root.after(0, lambda: self.disk_progress.config(value=100))
                    self.root.after(0, lambda: self.set_progress_success(self.disk_progress))
                    self.root.after(0, lambda: self.disk_progress_label.config(text="Completed successfully"))
                else:
                    self.root.after(0, lambda: self.disk_progress.config(value=0))
                    self.root.after(0, lambda: self.set_progress_error(self.disk_progress))
                    self.root.after(0, lambda: self.disk_progress_label.config(text="Failed - Check logs"))

        thread = threading.Thread(target=clone_thread, daemon=True)
        thread.start()


def main():
    root = tk.Tk()
    app = DiskClonerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
