import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import sqlite3
import datetime
import threading
import time
import keyword
import re
import requests

# ---------------- DATABASE ----------------
conn = sqlite3.connect("study_notes.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS notes(
id INTEGER PRIMARY KEY AUTOINCREMENT,
lesson TEXT,
content TEXT,
study_date TEXT,
hard INTEGER
)
""")

conn.commit()

# ---------------- SYNTAX HIGHLIGHT ----------------
def highlight(event=None):

    editor.tag_remove("keyword", "1.0", "end")
    editor.tag_remove("string", "1.0", "end")
    editor.tag_remove("comment", "1.0", "end")

    editor.tag_config("keyword", foreground="cyan")
    editor.tag_config("string", foreground="green")
    editor.tag_config("comment", foreground="gray")

    content = editor.get("1.0","end")

    for word in keyword.kwlist:

        start = "1.0"

        while True:

            pos = editor.search(word, start, stopindex="end")

            if not pos:
                break

            end = f"{pos}+{len(word)}c"

            editor.tag_add("keyword", pos, end)

            start = end

    start = "1.0"

    while True:

        pos = editor.search("#", start, stopindex="end")

        if not pos:
            break

        end = editor.search("\n", pos, stopindex="end")

        if not end:
            end = "end"

        editor.tag_add("comment", pos, end)

        start = end

    for match in re.finditer(r'".*?"|\'.*?\'', content):

        start = f"1.0+{match.start()}c"
        end = f"1.0+{match.end()}c"

        editor.tag_add("string", start, end)

# ---------------- SAVE NOTE ----------------
def save_note():

    lesson = lesson_entry.get()
    content = editor.get("1.0","end")
    study_date = date_entry.get()
    hard = hard_var.get()

    cursor.execute("""
    INSERT INTO notes(lesson,content,study_date,hard)
    VALUES (?,?,?,?)
    """,(lesson,content,study_date,hard))

    conn.commit()

    load_notes()

    messagebox.showinfo("Saved","Note saved")

# ---------------- DELETE NOTE ----------------
def delete_note():

    selection = listbox.curselection()

    if not selection:
        messagebox.showwarning("Warning","Select a note first")
        return

    index = selection[0]

    cursor.execute("SELECT id FROM notes ORDER BY id")
    rows = cursor.fetchall()

    note_id = rows[index][0]

    confirm = messagebox.askyesno("Delete","Delete this note?")

    if confirm:

        cursor.execute("DELETE FROM notes WHERE id=?", (note_id,))
        conn.commit()

        load_notes()

        editor.delete("1.0","end")

# ---------------- LOAD NOTES ----------------
def load_notes():

    listbox.delete(0,tk.END)

    cursor.execute("SELECT lesson FROM notes ORDER BY id")

    rows = cursor.fetchall()

    for r in rows:
        listbox.insert(tk.END,r[0])

# ---------------- SHOW NOTE ----------------
def show_note(event):

    selection = listbox.curselection()

    if not selection:
        return

    index = selection[0]

    cursor.execute("SELECT lesson,content,study_date,hard FROM notes ORDER BY id")

    rows = cursor.fetchall()

    note = rows[index]

    lesson_entry.delete(0,"end")
    lesson_entry.insert(0,note[0])

    date_entry.delete(0,"end")
    date_entry.insert(0,note[2])

    hard_var.set(note[3])

    editor.delete("1.0","end")
    editor.insert("1.0",note[1])

# ---------------- LOCAL AI SUMMARY ----------------
def ai_summary():

    text = editor.get("1.0","end")

    if not text.strip():
        messagebox.showwarning("Warning","Write something first")
        return

    try:

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": f"Summarize this study note in simple words:\n{text}",
                "stream": False
            }
        )

        summary = response.json()["response"]

        messagebox.showinfo("AI Summary", summary)

    except Exception as e:

        messagebox.showerror(
            "AI Error",
            "Make sure Ollama is installed and 'ollama run llama3' is running."
        )

# ---------------- REMINDER ----------------
def reminder():

    conn2 = sqlite3.connect("study_notes.db")
    cursor2 = conn2.cursor()

    while True:

        today = str(datetime.date.today())

        cursor2.execute("""
        SELECT lesson FROM notes
        WHERE study_date=?
        """,(today,))

        rows = cursor2.fetchall()

        for r in rows:
            print("🔔 Today study:", r[0])

        time.sleep(3600)

# ---------------- GUI ----------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Python Study Notes + Local AI")
app.geometry("1000x600")

top = ctk.CTkFrame(app)
top.pack(fill="x", padx=10, pady=10)

lesson_entry = ctk.CTkEntry(top, placeholder_text="Lesson name")
lesson_entry.pack(side="left", padx=10)

date_entry = ctk.CTkEntry(top, placeholder_text="Study date YYYY-MM-DD")
date_entry.pack(side="left", padx=10)

hard_var = tk.IntVar()

hard_checkbox = ctk.CTkCheckBox(top, text="Hard topic", variable=hard_var)
hard_checkbox.pack(side="left", padx=10)

save_btn = ctk.CTkButton(top, text="Save", command=save_note)
save_btn.pack(side="left", padx=10)

delete_btn = ctk.CTkButton(top, text="Delete", command=delete_note)
delete_btn.pack(side="left", padx=10)

ai_btn = ctk.CTkButton(top, text="AI Summary", command=ai_summary)
ai_btn.pack(side="left", padx=10)

main = ctk.CTkFrame(app)
main.pack(fill="both", expand=True, padx=10, pady=10)

listbox = tk.Listbox(main, width=30, bg="#1e1e1e", fg="white")
listbox.pack(side="left", fill="y")

listbox.bind("<<ListboxSelect>>", show_note)

editor = tk.Text(main, font=("Consolas",12), bg="#1e1e1e", fg="white")
editor.pack(fill="both", expand=True)

editor.bind("<KeyRelease>", highlight)

load_notes()

thread = threading.Thread(target=reminder, daemon=True)
thread.start()

app.mainloop()