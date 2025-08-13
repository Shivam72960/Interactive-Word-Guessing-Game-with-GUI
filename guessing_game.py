import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import random
import time
import os
from datetime import datetime

# ---------------- WORD BANK ---------------- #
CATEGORIES = {
    "Animals": {
        "Easy": ["tiger", "zebra", "panda", "camel", "horse", "eagle", "koala", "shark"],
        "Medium": ["monkey", "rabbit", "donkey", "otter", "parrot", "walrus", "iguana"],
        "Hard": ["elephant", "butterfly", "crocodile", "chimpanzee", "hippopotamus"]
    },
    "Countries": {
        "Easy": ["india", "nepal", "spain", "china", "italy", "japan"],
        "Medium": ["france", "germany", "canada", "brazil", "sweden", "norway"],
        "Hard": ["argentina", "australia", "portugal", "singapore", "netherlands"]
    },
    "Food": {
        "Easy": ["apple", "bread", "mango", "pizza", "pasta", "noodles"],
        "Medium": ["bottle", "cookie", "tomato", "banana", "omelet", "walnut"],
        "Hard": ["croissant", "lasagna", "guacamole", "cheesecake", "macaroni"]
    },
    "Tech": {
        "Easy": ["mouse", "cable", "phone", "clock", "chips", "panel"],
        "Medium": ["python", "laptop", "server", "router", "backup", "driver"],
        "Hard": ["algorithm", "database", "compiler", "encryption", "protocol"]
    }
}

# -------------- GAME CONFIG -------------- #
DIFFICULTY_CONFIG = {
    "Easy":   {"time": 40, "lives": 6, "per_wrong_penalty": 1},
    "Medium": {"time": 30, "lives": 5, "per_wrong_penalty": 2},
    "Hard":   {"time": 20, "lives": 4, "per_wrong_penalty": 3},
}

ROUNDS_TOTAL = 5                  # total rounds in a session
HINT_PENALTY = 2                  # score penalty per hint
MAX_HINTS_PER_ROUND = 2
BONUS_PER_SECOND_LEFT = 1         # bonus score added per second left when guessed correctly
LEADERBOARD_FILE = "leaderboard.txt"
TOP_N = 10                        # show top 10 scores

# -------------- GAME STATE -------------- #
secret = ""
attempt = 0
score = 0
time_left = 0
timer_running = False
round_no = 0
lives_left = 0
hints_used = 0
revealed_indices = set()
total_time_for_round = 0

# -------------- UTILITIES -------------- #
def choose_word(category, difficulty):
    words = CATEGORIES.get(category, {}).get(difficulty, [])
    if not words:
        # fallback to any available words if misconfigured
        words = sum(CATEGORIES.get(category, {}).values(), [])
    return random.choice(words) if words else "python"

def mask_from_guess(guess, secret_word):
    """Show correct letters in correct positions; '_' elsewhere (same as your original logic)."""
    hint = []
    for i, ch in enumerate(secret_word):
        if i < len(guess) and guess[i] == secret_word[i]:
            hint.append(guess[i])
        elif i in revealed_indices:
            hint.append(secret_word[i])
        else:
            hint.append("_")
    return "".join(hint)

def reveal_random_letter():
    """Reveal a random unrevealed letter position."""
    global hints_used, score
    if not secret:
        return
    if hints_used >= MAX_HINTS_PER_ROUND:
        messagebox.showinfo("Hint", f"Max {MAX_HINTS_PER_ROUND} hints already used in this round.")
        return

    candidates = [i for i in range(len(secret)) if i not in revealed_indices]
    if not candidates:
        messagebox.showinfo("Hint", "All letters are already revealed!")
        return

    idx = random.choice(candidates)
    revealed_indices.add(idx)
    hints_used += 1
    # penalty
    score -= HINT_PENALTY
    score_label.config(text=f"Score: {score}")
    update_hint_label()

def update_hint_label(current_guess=""):
    masked = mask_from_guess(current_guess, secret)
    hint_label.config(text="Hint: " + masked)

def update_lives():
    lives_label.config(text=f"Lives: {lives_left}")

def update_round():
    round_label.config(text=f"Round: {round_no}/{ROUNDS_TOTAL}")

def read_leaderboard():
    entries = []
    if os.path.exists(LEADERBOARD_FILE):
        try:
            with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # format: timestamp|name|score
                    parts = line.split("|")
                    if len(parts) == 3:
                        ts, name, sc = parts
                        try:
                            sc = int(sc)
                        except:
                            sc = 0
                        entries.append((ts, name, sc))
        except:
            pass
    # sort by score desc
    entries.sort(key=lambda x: x[2], reverse=True)
    return entries[:TOP_N]

def write_leaderboard(name, sc):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LEADERBOARD_FILE, "a", encoding="utf-8") as f:
            f.write(f"{ts}|{name}|{sc}\n")
    except:
        pass

def show_leaderboard():
    entries = read_leaderboard()
    if not entries:
        messagebox.showinfo("Leaderboard", "No scores yet. Be the first!")
        return
    text = "🏆 Top Scores:\n\n"
    for i, (ts, name, sc) in enumerate(entries, start=1):
        text += f"{i}. {name} — {sc}  ({ts})\n"
    messagebox.showinfo("Leaderboard", text)

# -------------- TIMER -------------- #
def update_timer():
    global time_left, timer_running
    if not timer_running:
        return
    if time_left > 0:
        time_left -= 1
        timer_label.config(text=f"Time Left: {time_left}s")
        # update progress bar
        if total_time_for_round > 0:
            progress = int(((total_time_for_round - time_left) / total_time_for_round) * 100)
            time_bar["value"] = progress
        root.after(1000, update_timer)
    else:
        messagebox.showinfo("Time's Up!", f"Out of time! The word was '{secret}'.")
        next_round_or_finish()

# -------------- GAME FLOW -------------- #
def start_game():
    """Start a brand new session (resets score and round count)."""
    global score, round_no
    score = 0
    round_no = 0
    score_label.config(text=f"Score: {score}")
    history_list.delete(0, tk.END)
    start_round()

def start_round():
    """Initialize a new round."""
    global secret, attempt, time_left, timer_running, lives_left, hints_used, revealed_indices, round_no, total_time_for_round

    # increment round count and check
    round_no += 1
    if round_no > ROUNDS_TOTAL:
        finish_game()
        return

    history_list.insert(tk.END, f"--- Starting Round {round_no} ---")
    history_list.see(tk.END)

    # reset round state
    attempt = 0
    hints_used = 0
    revealed_indices = set()

    difficulty = difficulty_var.get()
    category = category_var.get()

    # time/lives based on difficulty config
    cfg = DIFFICULTY_CONFIG.get(difficulty, DIFFICULTY_CONFIG["Easy"])
    time_left = cfg["time"]
    lives_left = cfg["lives"]
    per_wrong_penalty = cfg["per_wrong_penalty"]  # kept if you want further customization
    timer_running = True

    # pick word
    secret = choose_word(category, difficulty)

    # UI refresh
    update_round()
    update_lives()
    guess_entry.delete(0, tk.END)
    timer_label.config(text=f"Time Left: {time_left}s")
    total_time_for_round = time_left
    time_bar["value"] = 0
    update_hint_label()

    # start ticking
    update_timer()

def check_guess():
    global attempt, score, timer_running, lives_left

    if not timer_running:
        messagebox.showinfo("Info", "Start a round first!")
        return

    guess = guess_entry.get().strip().lower()
    if not guess:
        return

    attempt += 1
    guess_entry.delete(0, tk.END)

    if guess == secret:
        # scoring: base + bonus per second left
        base_points = 10
        bonus = time_left * BONUS_PER_SECOND_LEFT
        gained = base_points + bonus
        score += gained
        score_label.config(text=f"Score: {score}")
        messagebox.showinfo("🎉 Correct!", f"You guessed it in {attempt} attempts!\n+{base_points} points\n+{bonus} time bonus")
        timer_running = False
        next_round_or_finish()
        return

    # wrong guess flow
    # update hint based on positional matches + revealed letters
    masked = mask_from_guess(guess, secret)
    history_list.insert(tk.END, f"Attempt {attempt}: {guess} -> {masked}")
    history_list.see(tk.END)
    update_hint_label(guess)

    # penalty + life lost
    cfg = DIFFICULTY_CONFIG.get(difficulty_var.get(), DIFFICULTY_CONFIG["Easy"])
    score -= cfg["per_wrong_penalty"]
    lives_left -= 1
    score_label.config(text=f"Score: {score}")
    update_lives()

    if lives_left <= 0:
        timer_running = False
        messagebox.showinfo("💥 Out of lives!", f"You lost! The word was '{secret}'.")
        next_round_or_finish()

def next_round_or_finish():
    """Move to next round or end the session."""
    global timer_running
    timer_running = False
    if round_no < ROUNDS_TOTAL:
        start_round()
    else:
        finish_game()

def finish_game():
    global timer_running
    timer_running = False
    # Ask for name, write leaderboard, show top scores
    name = simpledialog.askstring("Game Over", f"Your total score: {score}\nEnter your name for the leaderboard:")
    if name:
        write_leaderboard(name.strip() or "Player", score)
    show_leaderboard()

def reset_session():
    """Reset everything (score, rounds, UI)."""
    global score, timer_running, round_no, time_left, lives_left, hints_used, revealed_indices
    timer_running = False
    score = 0
    round_no = 0
    time_left = 0
    lives_left = 0
    hints_used = 0
    revealed_indices = set()
    score_label.config(text=f"Score: {score}")
    hint_label.config(text="")
    guess_entry.delete(0, tk.END)
    history_list.delete(0, tk.END)
    timer_label.config(text="Time Left: 0s")
    time_bar["value"] = 0
    update_round()
    update_lives()

# -------------- UI -------------- #
root = tk.Tk()
root.title("🔑 Password Guessing Game — Advanced")
root.geometry("720x640")
root.configure(bg="#1e1e2f")

# Title
title_label = tk.Label(root, text="🔑 Password Guessing Game (Advanced)", font=("Arial", 18, "bold"),
                       bg="#1e1e2f", fg="#00ffcc")
title_label.pack(pady=10)

# Top controls frame
top_frame = tk.Frame(root, bg="#1e1e2f")
top_frame.pack(pady=4)

# Difficulty
tk.Label(top_frame, text="Difficulty:", font=("Arial", 12), bg="#1e1e2f", fg="white").grid(row=0, column=0, padx=6, pady=4, sticky="e")
difficulty_var = tk.StringVar(value="Easy")
diff_menu = tk.OptionMenu(top_frame, difficulty_var, "Easy", "Medium", "Hard")
diff_menu.grid(row=0, column=1, padx=6, pady=4, sticky="w")

# Category
tk.Label(top_frame, text="Category:", font=("Arial", 12), bg="#1e1e2f", fg="white").grid(row=0, column=2, padx=6, pady=4, sticky="e")
category_var = tk.StringVar(value="Animals")
cat_menu = tk.OptionMenu(top_frame, category_var, *CATEGORIES.keys())
cat_menu.grid(row=0, column=3, padx=6, pady=4, sticky="w")

# Round/Score/Lives info
info_frame = tk.Frame(root, bg="#1e1e2f")
info_frame.pack(pady=6)
round_label = tk.Label(info_frame, text=f"Round: 0/{ROUNDS_TOTAL}", font=("Arial", 12), bg="#1e1e2f", fg="yellow")
round_label.pack(side=tk.LEFT, padx=10)
timer_label = tk.Label(info_frame, text="Time Left: 0s", font=("Arial", 12), bg="#1e1e2f", fg="yellow")
timer_label.pack(side=tk.LEFT, padx=10)
score_label = tk.Label(info_frame, text="Score: 0", font=("Arial", 12), bg="#1e1e2f", fg="yellow")
score_label.pack(side=tk.LEFT, padx=10)
lives_label = tk.Label(info_frame, text="Lives: 0", font=("Arial", 12), bg="#1e1e2f", fg="yellow")
lives_label.pack(side=tk.LEFT, padx=10)

# Timer progress bar
bar_frame = tk.Frame(root, bg="#1e1e2f")
bar_frame.pack(pady=2)
time_bar = ttk.Progressbar(bar_frame, orient="horizontal", length=500, mode="determinate")
time_bar.pack(pady=2)

# Hint
hint_label = tk.Label(root, text="", font=("Arial", 16, "bold"), bg="#1e1e2f", fg="white")
hint_label.pack(pady=10)

# Guess Entry
entry_frame = tk.Frame(root, bg="#1e1e2f")
entry_frame.pack(pady=2)
tk.Label(entry_frame, text="Enter your guess:", font=("Arial", 12), bg="#1e1e2f", fg="white").grid(row=0, column=0, padx=6)
guess_entry = tk.Entry(entry_frame, font=("Arial", 14), width=24)
guess_entry.grid(row=0, column=1, padx=6)

# Buttons
btn_frame = tk.Frame(root, bg="#1e1e2f")
btn_frame.pack(pady=10)
tk.Button(btn_frame, text="▶ Start New Game", command=start_game, font=("Arial", 12), bg="#00ffcc").grid(row=0, column=0, padx=8, pady=4)
tk.Button(btn_frame, text="💡 Hint (-2)", command=reveal_random_letter, font=("Arial", 12), bg="#ffaa00").grid(row=0, column=1, padx=8, pady=4)
tk.Button(btn_frame, text="✓ Submit Guess", command=check_guess, font=("Arial", 12), bg="#66ccff").grid(row=0, column=2, padx=8, pady=4)
tk.Button(btn_frame, text="🔁 Reset Session", command=reset_session, font=("Arial", 12), bg="#ff6666").grid(row=0, column=3, padx=8, pady=4)
tk.Button(btn_frame, text="🏆 Leaderboard", command=show_leaderboard, font=("Arial", 12), bg="#b588f7").grid(row=0, column=4, padx=8, pady=4)

# History
tk.Label(root, text="Guess History:", font=("Arial", 12), bg="#1e1e2f", fg="white").pack(pady=4)
history_list = tk.Listbox(root, width=70, height=12, font=("Arial", 10))
history_list.pack(pady=6)

# Start Tk loop
root.mainloop()

