import os
import pickle
import json
import shutil
import threading
from datetime import datetime
from tkinter import messagebox, filedialog, Toplevel
import customtkinter as ctk
from PIL import Image, ImageTk
import sys

from core.search_engine import SearchEngine  # <-- Core séparé

# -------------------------------
# Config
# -------------------------------
CACHE_FILE = 'searchy_cache.pkl'
HISTORY_FILE = 'searchy_history.json'
FAVORITES_FILE = 'searchy_favorites.pkl'
ASSETS_DIR = "assets"  # dossier pour icône et images PDF

# -------------------------------
# Utils
# -------------------------------
def resource_path(relative_path):
    """Pour exe PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_user_profile():
    return os.path.expanduser('~')

def get_scan_paths():
    return [os.path.join(get_user_profile(), folder) for folder in FOLDERS_TO_SCAN]

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'rb') as f:
                return pickle.load(f)
        except:
            return None
    return None

def save_cache(file_list):
    try:
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump(file_list, f)
    except:
        pass

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(history):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f)
    except:
        pass

def load_favorites():
    if os.path.exists(FAVORITES_FILE):
        try:
            with open(FAVORITES_FILE, 'rb') as f:
                return pickle.load(f)
        except:
            return []
    return []

def save_favorites(favorites):
    try:
        with open(FAVORITES_FILE, 'wb') as f:
            pickle.dump(favorites, f)
    except:
        pass

# -------------------------------
# UI & Actions
# -------------------------------
def show_credits():
    w = ctk.CTkToplevel(root)
    w.title("Crédits")
    w.geometry("400x300")
    
    credits_text = """
Searchy v0.5
Développé par : ZenoqPNG
Framework UI : CustomTkinter
Images : PIL
PDF : pdf2image
Python 3.14
    
Merci d'utiliser Searchy !
"""
    label = ctk.CTkLabel(w, text=credits_text, justify="left", font=("Helvetica", 14))
    label.pack(padx=20, pady=20)

def show_preview(path, event):
    try:
        if path.lower().endswith(('.png','.jpg','.jpeg','.gif','.bmp')):
            img = Image.open(path)
            img.thumbnail((200,200))
            img_tk = ImageTk.PhotoImage(img)
            preview = Toplevel(root)
            preview.title("Aperçu")
            preview.geometry("220x220")
            lbl = ctk.CTkLabel(preview,image=img_tk)
            lbl.image = img_tk
            lbl.pack()
        elif path.lower().endswith('.pdf'):
            from pdf2image import convert_from_path
            pages = convert_from_path(path, first_page=1, last_page=1, size=(200,None))
            img_tk = ImageTk.PhotoImage(pages[0])
            preview = Toplevel(root)
            preview.title("Aperçu PDF")
            preview.geometry("220x300")
            lbl = ctk.CTkLabel(preview,image=img_tk)
            lbl.image = img_tk
            lbl.pack()
    except ImportError:
        messagebox.showinfo("Aperçu","Installez pdf2image pour les aperçus PDF")
    except:
        pass

def open_file(path):
    if os.path.exists(path):
        try:
            os.startfile(path)
        except:
            messagebox.showinfo("Open", f"Impossible d’ouvrir {path}")

def delete_file(path):
    if messagebox.askyesno("Supprimer", f"Supprimer {path} ?"):
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            rescan_files_with_anim()
        except:
            messagebox.showerror("Erreur", "Impossible de supprimer.")

def move_file(path):
    dest = filedialog.askdirectory()
    if dest:
        try:
            shutil.move(path,dest)
            rescan_files_with_anim()
        except:
            messagebox.showerror("Erreur", "Impossible de déplacer.")

def context_menu(event,path):
    menu = ctk.CTkMenu(root)
    menu.add_command(label="Ouvrir", command=lambda: open_file(path))
    menu.add_command(label="Ouvrir dossier parent", command=lambda: os.startfile(os.path.dirname(path)))
    menu.add_command(label="Copier chemin", command=lambda: root.clipboard_append(path))
    menu.add_command(label="Déplacer", command=lambda: move_file(path))
    menu.add_command(label="Supprimer", command=lambda: delete_file(path))
    menu.post(event.x_root,event.y_root)

def show_toast(title,message):
    t = Toplevel(root)
    t.title(title)
    t.geometry("300x100")
    t.resizable(False,False)
    ctk.CTkLabel(t,text=message,font=("Helvetica",14)).pack(pady=20)
    root.after(3000,t.destroy)

def sort_results(results,sort_by):
    if sort_by=="name":
        return sorted(results,key=lambda x:x[0].lower())
    elif sort_by=="size":
        return sorted(results,key=lambda x: os.path.getsize(x[1]) if os.path.isfile(x[1]) else 0,reverse=True)
    elif sort_by=="date":
        return sorted(results,key=lambda x: os.path.getmtime(x[1]) if os.path.isfile(x[1]) else 0,reverse=True)
    return results

def update_results(sort_by="name", live=False):
    if not live:
        for l in result_labels:
            l.destroy()
        result_labels.clear()

    sorted_results = sort_results(search_results, sort_by)

    appearance = ctk.get_appearance_mode()  # "light" ou "dark"
    text_color = "#000000" if appearance == "light" else "#ffffff"
    bg_colors = ("#f0f0f0", "#e0e0e0") if appearance == "light" else ("#2a2a2a", "#1f1f1f")

    for i, (name, path) in enumerate(sorted_results[len(result_labels):] if live else sorted_results):
        icon = "📁" if os.path.isdir(path) else "📄"
        bg = bg_colors[i % 2]
        size = f" ({os.path.getsize(path)//1024} KB)" if os.path.isfile(path) else ""
        date = f" - {datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d')}" if os.path.isfile(path) else ""

        lbl = ctk.CTkLabel(result_listbox,
                            text=f"{icon} {name}{size}{date}",
                            font=("Helvetica", 14),
                            fg_color=bg,
                            text_color=text_color,
                            corner_radius=5)
        lbl.pack(fill=ctk.X, pady=2, padx=5)
        lbl.bind("<Double-Button-1>", lambda e, p=path: open_file(p))
        lbl.bind("<Button-3>", lambda e, p=path: context_menu(e, p))
        lbl.bind("<Enter>", lambda e, l=lbl: l.configure(fg_color="#d0d0d0"))
        lbl.bind("<Leave>", lambda e, l=lbl, c=bg: l.configure(fg_color=c))
        lbl.bind("<Motion>", lambda e, p=path: show_preview(p, e))
        result_labels.append(lbl)

def perform_search():
    global search_results
    query = search_entry.get().strip()
    if not query:
        messagebox.showwarning("Searchy","Tape quelque chose !")
        return
    filters = engine.parse_smart_search(query)
    content_search = content_var.get()
    search_results[:] = engine.search_files(filters, content_search)
    history = load_history()
    if query not in history:
        history.append(query)
        if len(history)>10:
            history.pop(0)
        save_history(history)
    update_results(sort_var.get() if 'sort_var' in globals() else "name")

def animate_button_click(button):
    w = button.cget("width")
    button.configure(width=w+10)
    root.after(100,lambda: button.configure(width=w))

def rescan_files_with_anim():
    animate_button_click(rescan_button)
    rescan_files()

def rescan_files():
    def scan_thread():
        progress_bar.pack(pady=10)
        progress_bar.set(0)
        def live_update(new_list):
            global engine
            engine.file_list = new_list
            update_results(sort_by=sort_var.get() if 'sort_var' in globals() else "name",live=True)
        engine.scan_files(live_update_callback=live_update)
        save_cache(engine.file_list)
        progress_bar.pack_forget()
        show_toast("Scan terminé",f"{len(engine.file_list)} éléments")
    threading.Thread(target=scan_thread,daemon=True).start()

def export_results():
    if not search_results:
        messagebox.showwarning("Export","Aucun résultat")
        return
    path = filedialog.asksaveasfilename(defaultextension=".txt",filetypes=[("Text files","*.txt")])
    if path:
        with open(path,'w',encoding='utf-8') as f:
            for n,p in search_results:
                f.write(f"{n}: {p}\n")
        show_toast("Export réussi","Résultats exportés")

def toggle_favorite(path):
    favs = load_favorites()
    if path in favs:
        favs.remove(path)
        show_toast("Favoris","Retiré")
    else:
        favs.append(path)
        show_toast("Favoris","Ajouté")
    save_favorites(favs)

def change_theme(value):
    ctk.set_appearance_mode(value)

def show_history():
    messagebox.showinfo("Historique", "Fonction à implémenter")

def show_favorites():
    messagebox.showinfo("Favoris", "Fonction à implémenter")

def manage_scan_paths():
    messagebox.showinfo("Dossiers à scanner", "Fonction à implémenter")

def scan_network():
    messagebox.showinfo("Scan réseau", "Fonction à implémenter")

def update_language(value):
    messagebox.showinfo("Langue", f"Langue changée en {value}")

# -------------------------------
# Initialisation
# -------------------------------
FOLDERS_TO_SCAN = ['Downloads', 'Desktop', 'Documents', 'Pictures', 'Music']

engine = SearchEngine(get_scan_paths())
cached = load_cache()
if cached:
    engine.file_list = cached
else:
    engine.scan_files()
    save_cache(engine.file_list)

search_results = []
result_labels = []

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Searchy")
root.geometry("1500x1000")
root.iconbitmap(resource_path(os.path.join("assets","searchy.ico")))

# --- UI setup reste le même ---
top_frame = ctk.CTkFrame(root,fg_color="transparent")
top_frame.pack(fill=ctk.X,padx=20,pady=10)

logo_label = ctk.CTkLabel(top_frame,text="SEARCHY",font=("Helvetica",36,"bold"),text_color="#007AFF")
logo_label.pack(side=ctk.LEFT)

theme_menu = ctk.CTkOptionMenu(top_frame, values=["light","dark","graphite","pastel"], command=change_theme)
theme_menu.pack(side=ctk.RIGHT,padx=10)

history_button = ctk.CTkButton(top_frame,text="📜 Historique",command=show_history,width=100,height=30,corner_radius=15)
history_button.pack(side=ctk.RIGHT,padx=10)

favorites_button = ctk.CTkButton(top_frame,text="⭐ Favoris",command=show_favorites,width=100,height=30,corner_radius=15)
favorites_button.pack(side=ctk.RIGHT)

credits_button = ctk.CTkButton(top_frame, text="💡 Crédits", command=lambda: show_credits(), width=100, height=30, corner_radius=15)
credits_button.pack(side=ctk.RIGHT, padx=10)

subtitle = ctk.CTkLabel(root,text="Recherche intelligente avec aperçus, filtres, et plus",font=("Helvetica",16),text_color="#666666")
subtitle.pack(pady=(0,20))

tabview = ctk.CTkTabview(root,width=1400,height=250)
tabview.pack(pady=10,padx=20)
tabview.add("Recherche")
tabview.add("Filtres")

# Recherche tab
search_frame = tabview.tab("Recherche")
search_entry = ctk.CTkEntry(search_frame,placeholder_text="Tapez votre recherche (nom:rapport, type:.txt, taille>1000)...",width=700,height=40,font=("Helvetica",16))
search_entry.pack(side=ctk.LEFT,padx=(0,10),pady=10)

content_var = ctk.BooleanVar()
content_check = ctk.CTkCheckBox(search_frame,text="Recherche dans contenu",variable=content_var)
content_check.pack(side=ctk.LEFT,pady=10)

search_button = ctk.CTkButton(search_frame,text="🔍 Rechercher",command=perform_search,width=150,height=40,corner_radius=20)
search_button.pack(side=ctk.LEFT,pady=10)

rescan_button = ctk.CTkButton(search_frame,text="🔄 Rescanner",command=rescan_files_with_anim,width=150,height=40,corner_radius=20)
rescan_button.pack(side=ctk.LEFT,padx=(10,0),pady=10)

export_button = ctk.CTkButton(search_frame,text="📤 Exporter",command=export_results,width=120,height=40,corner_radius=20)
export_button.pack(side=ctk.LEFT,padx=(10,0),pady=10)

progress_bar = ctk.CTkProgressBar(search_frame,width=400)
progress_bar.pack(side=ctk.LEFT,padx=(20,0),pady=10)
progress_bar.pack_forget()

# Result list
result_listbox = ctk.CTkScrollableFrame(root,width=1400,height=600)
result_listbox.pack(padx=20,pady=20)

# Sort
sort_var = ctk.StringVar(value="name")
sort_menu = ctk.CTkOptionMenu(root,values=["name","size","date"],variable=sort_var,command=lambda x:update_results(sort_var.get()))
sort_menu.pack()

filters_frame = tabview.tab("Filtres")
ctk.CTkLabel(filters_frame, text="Filtres avancés", font=("Helvetica",18)).pack(pady=10)

ctk.CTkButton(filters_frame, text="📁 Gérer dossiers à scanner", command=manage_scan_paths).pack(pady=5)
ctk.CTkButton(filters_frame, text="🌐 Scanner réseau", command=scan_network).pack(pady=5)

lang_var = ctk.StringVar(value="en")
ctk.CTkOptionMenu(filters_frame, values=["en","es","de"], variable=lang_var, command=update_language).pack(pady=5)
# -------------------------------
# Main loop
# -------------------------------
root.mainloop()
