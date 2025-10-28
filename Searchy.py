import os
import pickle
import json
import shutil
import re
import threading
from datetime import datetime
from tkinter import messagebox, filedialog, Toplevel
import customtkinter as ctk
from PIL import Image, ImageTk
import sys

# -------------------------------
# Config
# -------------------------------
FOLDERS_TO_SCAN = ['Downloads', 'Desktop', 'Documents', 'Pictures', 'Music']
CACHE_FILE = 'searchy_cache.pkl'
HISTORY_FILE = 'searchy_history.json'
FAVORITES_FILE = 'searchy_favorites.pkl'
ASSETS_DIR = "assets"  # dossier pour icônes et images

# -------------------------------
# Utils
# -------------------------------
def resource_path(relative_path):
    """Pour accéder aux assets même depuis le .exe"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_user_profile():
    return os.path.expanduser('~')

def get_scan_paths():
    user_profile = get_user_profile()
    return [os.path.join(user_profile, folder) for folder in FOLDERS_TO_SCAN]

def scan_files(progress_callback=None, live_update_callback=None):
    files = []
    for folder in get_scan_paths():
        if os.path.exists(folder):
            for root_dir, dirs, filenames in os.walk(folder):
                for f in filenames:
                    path = os.path.join(root_dir, f)
                    files.append((f, path))
                    if live_update_callback:
                        live_update_callback(files)
                for d in dirs:
                    path = os.path.join(root_dir, d)
                    files.append((d, path))
                    if live_update_callback:
                        live_update_callback(files)
    return files

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE,'rb') as f:
                return pickle.load(f)
        except:
            return None
    return None

def save_cache(files):
    with open(CACHE_FILE,'wb') as f:
        pickle.dump(files,f)

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE,'r',encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(history):
    with open(HISTORY_FILE,'w',encoding='utf-8') as f:
        json.dump(history,f)

def load_favorites():
    if os.path.exists(FAVORITES_FILE):
        try:
            with open(FAVORITES_FILE,'rb') as f:
                return pickle.load(f)
        except:
            return []
    return []

def save_favorites(favs):
    with open(FAVORITES_FILE,'wb') as f:
        pickle.dump(favs,f)

def parse_smart_search(query):
    filters = {}
    name_match = re.search(r'nom:(\w+)', query)
    if name_match:
        filters['name'] = name_match.group(1)
        query = re.sub(r'nom:\w+', '', query).strip()
    type_match = re.search(r'type:(\.\w+)', query)
    if type_match:
        filters['extension'] = type_match.group(1)
        query = re.sub(r'type:\.\w+', '', query).strip()
    size_match = re.search(r'taille([><=])(\d+)', query)
    if size_match:
        op,size = size_match.groups()
        if op == '>': filters['min_size'] = size
        elif op == '<': filters['max_size'] = size
        query = re.sub(r'taille[><=]\d+','',query).strip()
    filters['keyword'] = query
    return filters

def search_files(files, filters, content_search=False):
    keyword = filters.get('keyword','').lower()
    results = []
    for name,path in files:
        match = True
        if keyword and keyword not in name.lower(): match=False
        if 'name' in filters and filters['name'].lower() not in name.lower(): match=False
        if 'extension' in filters and not name.lower().endswith(filters['extension'].lower()): match=False
        if 'min_size' in filters and os.path.isfile(path):
            if os.path.getsize(path) < int(filters['min_size'])*1024: match=False
        if 'max_size' in filters and os.path.isfile(path):
            if os.path.getsize(path) > int(filters['max_size'])*1024: match=False
        if content_search and os.path.isfile(path) and path.lower().endswith(('.txt','.py','.md','.html','.css','.js')):
            try:
                with open(path,'r',encoding='utf-8',errors='ignore') as f:
                    if keyword not in f.read().lower(): match=False
            except: match=False
        if match: results.append((name,path))
    return results

# -------------------------------
# UI & Actions
# -------------------------------
def open_file(path):
    if os.path.exists(path):
        try: os.startfile(path)
        except: messagebox.showinfo("Open", f"Impossible d’ouvrir {path}")

def show_credits():
    w = ctk.CTkToplevel(root)
    w.title("Crédits")
    w.geometry("400x300")
    text = """
Searchy v0.3
Dev: ZenoqPNG
UI: CustomTkinter
Images: PIL
PDF: pdf2image
Python 3.14+
Merci d'utiliser Searchy !
"""
    ctk.CTkLabel(w,text=text,justify="left").pack(padx=20,pady=20)

def show_preview(path,event):
    try:
        if path.lower().endswith(('.png','.jpg','.jpeg','.gif','.bmp')):
            img = Image.open(path)
            img.thumbnail((200,200))
            img_tk = ImageTk.PhotoImage(img)
            win = Toplevel(root)
            win.title("Preview")
            win.geometry("220x220")
            lbl = ctk.CTkLabel(win,image=img_tk)
            lbl.image = img_tk
            lbl.pack()
        elif path.lower().endswith('.pdf'):
            from pdf2image import convert_from_path
            pages = convert_from_path(path,first_page=1,last_page=1,size=(200,None))
            img_tk = ImageTk.PhotoImage(pages[0])
            win = Toplevel(root)
            win.title("PDF Preview")
            win.geometry("220x300")
            lbl = ctk.CTkLabel(win,image=img_tk)
            lbl.image = img_tk
            lbl.pack()
    except ImportError:
        messagebox.showinfo("Preview","Installez pdf2image pour PDF")
    except:
        pass

def toggle_favorite(path):
    favs = load_favorites()
    if path in favs: favs.remove(path)
    else: favs.append(path)
    save_favorites(favs)

def perform_search():
    global search_results
    query = search_entry.get().strip()
    if not query: messagebox.showwarning("Searchy","Tapez quelque chose !"); return
    filters = parse_smart_search(query)
    content_search = content_var.get()
    search_results = search_files(file_list,filters,content_search)
    history = load_history()
    if query not in history:
        history.append(query)
        if len(history)>10: history.pop(0)
        save_history(history)
    update_results()

def update_results():
    for l in result_labels: l.destroy()
    result_labels.clear()
    for name,path in search_results:
        icon = "📁" if os.path.isdir(path) else "📄"
        lbl = ctk.CTkLabel(result_listbox,text=f"{icon} {name}",font=("Helvetica",14))
        lbl.pack(fill=ctk.X,pady=2,padx=5)
        lbl.bind("<Double-Button-1>",lambda e,p=path: open_file(p))
        lbl.bind("<Button-3>",lambda e,p=path: toggle_favorite(p))
        result_labels.append(lbl)

# -------------------------------
# Init
# -------------------------------
file_list = load_cache()
if file_list is None:
    file_list = scan_files()
    save_cache(file_list)

search_results = []
result_labels = []

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Searchy v0.3")
root.geometry("1200x800")
root.iconbitmap(resource_path(os.path.join("assets","searchy.ico")))

# Top UI
top_frame = ctk.CTkFrame(root,fg_color="transparent")
top_frame.pack(fill=ctk.X,padx=20,pady=10)

ctk.CTkLabel(top_frame,text="SEARCHY",font=("Helvetica",36,"bold"),text_color="#007AFF").pack(side=ctk.LEFT)
ctk.CTkButton(top_frame,text="💡 Crédits",command=show_credits,width=100,height=30).pack(side=ctk.RIGHT,padx=10)

# Search
search_entry = ctk.CTkEntry(root,placeholder_text="nom:rapport type:.txt taille>1000...",width=700,height=40)
search_entry.pack(pady=10)
content_var = ctk.BooleanVar()
ctk.CTkCheckBox(root,text="Recherche dans contenu",variable=content_var).pack()
ctk.CTkButton(root,text="🔍 Rechercher",command=perform_search,width=150,height=40).pack(pady=5)

# Results
result_listbox = ctk.CTkScrollableFrame(root,width=1100,height=600)
result_listbox.pack(pady=10)
result_labels = []

root.mainloop()
