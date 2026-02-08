import PyInstaller.__main__
import customtkinter
import os
import shutil

# Get customtkinter path for add-data
ctk_path = os.path.dirname(customtkinter.__file__)

# Define separator based on OS
sep = ";" if os.name == "nt" else ":"

print("Building executable...")

PyInstaller.__main__.run([
    'folder_icon_changer.py',
    '--name=IconChanger',
    '--onefile',
    '--windowed',  # No console window
    f'--add-data={ctk_path}{sep}customtkinter', # Add ctk themes
    f'--add-data=icons{sep}icons', # Add icons folder
    '--hidden-import=PIL._tkinter_finder', # Sometimes needed
    '--hidden-import=cairosvg',
    '--hidden-import=packaging',
    '--clean',
])

print("Build complete. Executable is in 'dist' folder.")
print("Ensure the 'icons' folder is present next to the executable when running.")
