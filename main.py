import random
from collections import Counter
import itertools

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.core.window import Window

# Standard-Würfelsymbole (mit Zahlen als Fallback für Android)
DICE_SYMBOLS = {1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6"}
TARGET_SCORE = 10000

# Farbdefinitionen (RGBA von 0 bis 1)
BG_MAIN = (0.12, 0.16, 0.23, 1)       # #1e293b
COLOR_HEADER = (0.2, 0.25, 0.33, 1)    # #334155
COLOR_BLUE = (0.23, 0.51, 0.96, 1)    # #3b82f6
COLOR_GREEN = (0.13, 0.77, 0.37, 1)   # #22c55e
COLOR_YELLOW = (0.92, 0.7, 0.03, 1)   # #eab308
COLOR_RED = (0.94, 0.27, 0.27, 1)      # #ef4444
COLOR_DISABLED = (0.39, 0.45, 0.55, 1) # #64748b
COLOR_KEPT = (0.28, 0.33, 0.41, 1)     # #475569


def evaluate_selection(selected_dice):
    """Wertet eine Liste ausgewählter Würfel nach den Spielregeln aus."""
    if not selected_dice:
        return 0, False, "Keine Würfel ausgewählt"

    counts = Counter(selected_dice)
    n = len(selected_dice)

    if n == 6 and set(selected_dice) == {1, 2, 3, 4, 5, 6}:
        return 4000, True, "Große Straße (4000 Pkt)"

    def calc_std(cnt_map):
        score, used, parts = 0, 0, []
        for val in sorted(cnt_map.keys()):
            cnt = cnt_map[val]
            num_triplets = cnt // 3
            rem = cnt % 3
            if num_triplets > 0:
                pts = (1000 if val == 1 else val * 100) * num_triplets
                parts.append(f"{num_triplets}x 3er {val}er ({pts} Pkt)")
                score += pts
                used += num_triplets * 3
            if rem > 0:
                if val == 1:
                    pts = rem * 100
                    parts.append(f"{rem}x 1er ({pts} Pkt)")
                    score += pts
                    used += rem
                elif val == 5:
                    pts = rem * 50
                    parts.append(f"{rem}x 5er ({pts} Pkt)")
                    score += pts
                    used += rem
        return score, used, parts

    std_score, std_used, std_parts = calc_std(counts)
    std_valid = std_used == n

    three_candidates = [val for val, cnt in counts.items() if cnt >= 3]
    best_fh_score, best_fh_desc, is_fh_valid = -1, "", False

    for val_3 in three_candidates:
        two_candidates = [
            val for val, cnt in counts.items()
            if (val != val_3 and cnt >= 2) or (val == val_3 and cnt >= 5)
        ]
        for val_2 in two_candidates:
            rem_counts = Counter(counts)
            rem_counts[val_3] -= 3
            rem_counts[val_2] -= 2
            rem_counts = Counter({k: v for k, v in rem_counts.items() if v > 0})

            rem_score, rem_used, rem_parts = calc_std(rem_counts)
            if rem_used == sum(rem_counts.values()):
                total_fh_score = 500 + rem_score
                desc_p = ["Full House (500 Pkt)"] + rem_parts
                if total_fh_score > best_fh_score:
                    best_fh_score = total_fh_score
                    best_fh_desc = ", ".join(desc_p)
                    is_fh_valid = True

    if is_fh_valid and std_valid:
        if best_fh_score >= std_score:
            return best_fh_score, True, best_fh_desc
        return std_score, True, ", ".join(std_parts)
    elif is_fh_valid:
        return best_fh_score, True, best_fh_desc
    elif std_valid:
        return std_score, True, ", ".join(std_parts)

    return 0, False, "Ungültige Kombination"


def has_any_scoring_option(roll_dice):
    """Prüft, ob im Wurf Zähler enthalten sind."""
    counts = Counter(roll_dice)
    n = len(roll_dice)
    if counts[1] > 0 or counts[5] > 0 or any(c >= 3 for c in counts.values()):
        return True
    if n == 6 and set(roll_dice) == {1, 2, 3, 4, 5, 6}:
        return True
    if n >= 5:
        vals = sorted(counts.values(), reverse=True)
        if len(vals) >= 2 and vals[0] >= 3 and vals[1] >= 2:
            return True
    return False


def bot_select_dice(active_values):
    """Wählt für die KI die punktbeste Würfelkombination."""
    n = len(active_values)
    score, is_valid, _ = evaluate_selection(active_values)
    if is_valid:
        return list(range(n))

    best_indices, best_pts = [], -1
    for r in range(n, 0, -1):
        for idx_tuple in itertools.combinations(range(n), r):
            sub_vals = [active_values[i] for i in idx_tuple]
            pts, valid, _ = evaluate_selection(sub_vals)
            if valid and pts > best_pts:
                best_pts = pts
                best_indices = list(idx_tuple)

    return best_indices


class DiceGameApp(App):
    def build(self):
        self.title = "Würfelspiel 10.000"
        Window.clearcolor = BG_MAIN

        self.mode = "bot"
        self.players = ["Spieler 1", "Computer (KI)"]
        self.scores = [0, 0]
        self.current_player_idx = 0

        self.turn_score = 0
        self.dice_values = [1] * 6
        self.dice_states = ["active"] * 6

        self.is_animating = False
        self.has_rolled_in_step = False
        self.must_pass_turn = False

        # Haupt-Layout
        root = BoxLayout(orientation='vertical', padding=15, spacing=10)

        # 1. Modus-Auswahl (8% der Fensterhöhe)
        mode_layout = BoxLayout(size_hint_y=0.08, spacing=5)
        mode_layout.add_widget(Label(text="Modus:", size_hint_x=0.25, bold=True, color=(0.6, 0.6, 0.7, 1)))

        self.btn_m1 = Button(text="1 Spieler", background_color=COLOR_HEADER, background_normal='')
        self.btn_m1.bind(on_press=lambda x: self._set_mode("1p"))
        mode_layout.add_widget(self.btn_m1)

        self.btn_m2 = Button(text="2 Spieler", background_color=COLOR_HEADER, background_normal='')
        self.btn_m2.bind(on_press=lambda x: self._set_mode("2p"))
        mode_layout.add_widget(self.btn_m2)

        self.btn_bot = Button(text="vs. KI", background_color=COLOR_BLUE, background_normal='')
        self.btn_bot.bind(on_press=lambda x: self._set_mode("bot"))
        mode_layout.add_widget(self.btn_bot)

        root.add_widget(mode_layout)

        # 2. Header / Punktestand (14% der Fensterhöhe)
        header = BoxLayout(orientation='vertical', size_hint_y=0.14, padding=5)
        self.lbl_scores = Label(text="Spieler 1: 0  |  Computer: 0", bold=True, font_size='16sp')
        self.lbl_turn_score = Label(text="Am Zug: Spieler 1  (Zug-Punkte: 0)", color=(0.2, 0.7, 1, 1), font_size='15sp')
        header.add_widget(self.lbl_scores)
        header.add_widget(self.lbl_turn_score)
        root.add_widget(header)

        # 3. Statuszeile (8% der Fensterhöhe)
        self.lbl_status = Label(text="Neues Spiel gestartet!", size_hint_y=0.08, font_size='13sp', halign='center')
        root.add_widget(self.lbl_status)

        # 4. Würfelgitter (35% der Fensterhöhe)
        dice_grid = GridLayout(cols=3, spacing=10, size_hint_y=0.35)
        self.dice_buttons = []

        for i in range(6):
            btn = Button(text="1", font_size='22sp', bold=True, background_normal='', background_color=(1, 1, 1, 1), color=(0, 0, 0, 1))
            btn.bind(on_press=lambda instance, idx=i: self._on_dice_click(idx))
            self.dice_buttons.append(btn)
            dice_grid.add_widget(btn)

        root.add_widget(dice_grid)

        # 5. Regelliste (10% der Fensterhöhe)
        rules_text = f"Ziel: {TARGET_SCORE} Pkt | 1=100, 5=50, 3er=100xAugenzahl\nFull House=500 | Straße=4000 | Alle 6 abgeräumt = Bestätigungswurf!"
        root.add_widget(Label(text=rules_text, size_hint_y=0.10, font_size='11sp', color=(0.6, 0.6, 0.7, 1), halign='center'))

        # 6. Aktions-Buttons (12% der Fensterhöhe)
        btn_layout = BoxLayout(size_hint_y=0.12, spacing=15)
        self.btn_roll = Button(text="Würfeln", bold=True, background_color=COLOR_BLUE, background_normal='')
        self.btn_roll.bind(on_press=lambda x: self._on_roll_btn_click())

        self.btn_bank = Button(text="Punkte sichern (min. 300)", bold=True, background_color=COLOR_DISABLED, background_normal='', disabled=True)
        self.btn_bank.bind(on_press=lambda x: self._bank_points())

        btn_layout.add_widget(self.btn_roll)
        btn_layout.add_widget(self.btn_bank)
        root.add_widget(btn_layout)

        self._reset_game()
        return root


    def _show_popup(self, title, message):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text=message, halign='center'))
        btn = Button(text="OK", size_hint_y=None, height=40)
        content.add_widget(btn)
        popup = Popup(title=title, content=content, size_hint=(0.8, 0.4))
        btn.bind(on_press=popup.dismiss)
        popup.open()

    def _set_mode(self, mode):
        self.mode = mode
        self.btn_m1.background_color = COLOR_BLUE if mode == "1p" else COLOR_HEADER
        self.btn_m2.background_color = COLOR_BLUE if mode == "2p" else COLOR_HEADER
        self.btn_bot.background_color = COLOR_BLUE if mode == "bot" else COLOR_HEADER

        if mode == "1p":
            self.players = ["Spieler 1"]
        elif mode == "2p":
            self.players = ["Spieler 1", "Spieler 2"]
        elif mode == "bot":
            self.players = ["Spieler 1", "Computer (KI)"]

        self._reset_game()

    def _reset_game(self):
        self.scores = [0] * len(self.players)
        self.current_player_idx = 0
        self._update_score_header()
        self._start_new_turn()

    def _update_score_header(self):
        if len(self.players) == 1:
            self.lbl_scores.text = f"Gesamtpunkte: {self.scores[0]}"
        else:
            self.lbl_scores.text = "  |  ".join([f"{self.players[i]}: {self.scores[i]}" for i in range(len(self.players))])

    def _start_new_turn(self):
        self.turn_score = 0
        self.dice_states = ["active"] * 6
        self.has_rolled_in_step = False
        self.must_pass_turn = False

        curr_player = self.players[self.current_player_idx]
        self.lbl_turn_score.text = f"Am Zug: {curr_player}  (Zug-Punkte: 0)"
        self.lbl_status.text = f"Zug von {curr_player}. Klicke auf 'Würfeln'."

        self.btn_roll.disabled = False
        self.btn_roll.text = "Würfeln"
        self.btn_bank.disabled = True
        self.btn_bank.background_color = COLOR_DISABLED

        self._update_dice_styles()

        if self.mode == "bot" and curr_player == "Computer (KI)":
            self.btn_roll.disabled = True
            self.btn_bank.disabled = True
            Clock.schedule_once(lambda dt: self._bot_turn_start(), 1.0)

    def _update_dice_styles(self):
        for i in range(6):
            state = self.dice_states[i]
            val = self.dice_values[i]
            btn = self.dice_buttons[i]
            btn.text = DICE_SYMBOLS[val]

            if state == "active":
                btn.background_color = (1, 1, 1, 1)
                btn.color = (0, 0, 0, 1)
                btn.disabled = False
            elif state == "selected":
                btn.background_color = COLOR_YELLOW
                btn.color = (0, 0, 0, 1)
                btn.disabled = False
            elif state == "kept":
                btn.background_color = COLOR_KEPT
                btn.color = (0.7, 0.7, 0.7, 1)
                btn.disabled = True

    def _on_roll_btn_click(self):
        if self.must_pass_turn:
            self._next_player_turn()
        else:
            self._roll_dice()

    def _roll_dice(self):
        if self.is_animating:
            return

        if self.has_rolled_in_step:
            selected_indices = [i for i in range(6) if self.dice_states[i] == "selected"]
            selected_values = [self.dice_values[i] for i in selected_indices]

            pts, is_valid, desc = evaluate_selection(selected_values)
            if not is_valid:
                self._show_popup("Auswahl ungültig", desc)
                return

            self.turn_score += pts
            for i in selected_indices:
                self.dice_states[i] = "kept"

            if self.dice_states.count("kept") == 6:
                self.dice_states = ["active"] * 6
                self.has_rolled_in_step = False
                self.lbl_status.text = f"Alle 6 Würfel abgeräumt ({self.turn_score} Pkt)! Bestätigungswurf..."

        self.is_animating = True
        self.btn_roll.disabled = True
        self.btn_bank.disabled = True
        self.anim_ticks = 10
        Clock.schedule_interval(self._animate_roll_tick, 0.045)

    def _animate_roll_tick(self, dt):
        if self.anim_ticks > 0:
            for i in range(6):
                if self.dice_states[i] == "active":
                    self.dice_values[i] = random.randint(1, 6)
            self._update_dice_styles()
            self.anim_ticks -= 1
            return True
        else:
            self.is_animating = False
            self.has_rolled_in_step = True
            self._finish_roll()
            return False

    def _finish_roll(self):
        active_indices = [i for i in range(6) if self.dice_states[i] == "active"]
        active_values = [self.dice_values[i] for i in active_indices]

        if len(active_values) == 6 and set(active_values) == {1, 2, 3, 4, 5, 6}:
            self.turn_score += 4000
            curr_player = self.players[self.current_player_idx]
            self.lbl_turn_score.text = f"Am Zug: {curr_player}  (Zug-Punkte: {self.turn_score})"

            if not (self.mode == "bot" and curr_player == "Computer (KI)"):
                self._show_popup("GROSSE STRASSE!", "+4.000 Punkte!\nBestätigungswurf erforderlich!")

            self.dice_states = ["active"] * 6
            self.has_rolled_in_step = False
            self._update_dice_styles()

            if self.mode == "bot" and curr_player == "Computer (KI)":
                Clock.schedule_once(lambda dt: self._bot_decision_step(), 1.2)
            else:
                self.btn_roll.disabled = False
            return

        if not has_any_scoring_option(active_values):
            self._update_dice_styles()
            self.turn_score = 0
            curr_player = self.players[self.current_player_idx]
            self.lbl_turn_score.text = f"Am Zug: {curr_player}  (Zug-Punkte: 0)"
            self.lbl_status.text = f"Fehlwurf für {curr_player}! Punkte verloren."
            self.has_rolled_in_step = False

            if self.mode == "bot" and curr_player == "Computer (KI)":
                Clock.schedule_once(lambda dt: self._next_player_turn(), 1.5)
            else:
                self.btn_roll.text = "Nächster Spieler"
                self.btn_roll.disabled = False
                self.must_pass_turn = True
            return

        if self.mode == "bot" and self.players[self.current_player_idx] == "Computer (KI)":
            Clock.schedule_once(lambda dt: self._bot_step_select_dice(), 1.0)
        else:
            self._update_turn_display()
            self.btn_roll.disabled = False

    def _next_player_turn(self):
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
        self._start_new_turn()

    def _on_dice_click(self, index):
        if self.mode == "bot" and self.players[self.current_player_idx] == "Computer (KI)":
            return
        if not self.has_rolled_in_step or self.is_animating or self.must_pass_turn:
            return

        state = self.dice_states[index]
        if state == "active":
            self.dice_states[index] = "selected"
        elif state == "selected":
            self.dice_states[index] = "active"

        self._update_dice_styles()
        self._update_turn_display()

    def _update_turn_display(self):
        selected_indices = [i for i in range(6) if self.dice_states[i] == "selected"]
        selected_values = [self.dice_values[i] for i in selected_indices]

        pts, is_valid, desc = evaluate_selection(selected_values)
        potential_turn_score = self.turn_score + pts

        curr_player = self.players[self.current_player_idx]
        self.lbl_turn_score.text = f"Am Zug: {curr_player}  (Zug-Punkte: {potential_turn_score})"

        total_cleared = self.dice_states.count("selected") + self.dice_states.count("kept")

        if selected_indices and is_valid:
            self.lbl_status.text = f"Auswahl: {desc} (+{pts} Pkt)"

        if potential_turn_score >= 300 and is_valid and total_cleared < 6:
            self.btn_bank.disabled = False
            self.btn_bank.background_color = COLOR_GREEN
        else:
            self.btn_bank.disabled = True
            self.btn_bank.background_color = COLOR_DISABLED

    def _bank_points(self):
        selected_indices = [i for i in range(6) if self.dice_states[i] == "selected"]
        selected_values = [self.dice_values[i] for i in selected_indices]

        pts = 0
        if selected_indices:
            pts, is_valid, desc = evaluate_selection(selected_values)
            if not is_valid:
                self._show_popup("Hinweis", desc)
                return

        final_turn_score = self.turn_score + pts
        if final_turn_score < 300:
            self._show_popup("Hinweis", "Mindestens 300 Punkte benötigt!")
            return

        self.scores[self.current_player_idx] += final_turn_score
        self._update_score_header()

        curr_player = self.players[self.current_player_idx]

        if self.scores[self.current_player_idx] >= TARGET_SCORE:
            self._show_popup("GEWONNEN!", f"{curr_player} gewinnt mit {self.scores[self.current_player_idx]} Punkten!")
            self._reset_game()
            return

        self._next_player_turn()

    # --- KI STEUERUNG ---
    def _bot_turn_start(self):
        self.lbl_status.text = "Computer würfelt..."
        self._roll_dice()

    def _bot_step_select_dice(self):
        active_indices = [i for i in range(6) if self.dice_states[i] == "active"]
        active_values = [self.dice_values[i] for i in active_indices]

        selected_sub_indices = bot_select_dice(active_values)
        for sub_idx in selected_sub_indices:
            real_idx = active_indices[sub_idx]
            self.dice_states[real_idx] = "selected"

        self._update_dice_styles()
        Clock.schedule_once(lambda dt: self._bot_decision_step(), 1.2)

    def _bot_decision_step(self):
        selected_indices = [i for i in range(6) if self.dice_states[i] == "selected"]
        selected_values = [self.dice_values[i] for i in selected_indices]

        if selected_indices:
            pts, _, _ = evaluate_selection(selected_values)
            self.turn_score += pts
            for i in selected_indices:
                self.dice_states[i] = "kept"

        if self.dice_states.count("kept") == 6:
            self.dice_states = ["active"] * 6
            self.has_rolled_in_step = False
            self._update_dice_styles()
            Clock.schedule_once(lambda dt: self._roll_dice(), 1.2)
            return

        remaining_dice_count = self.dice_states.count("active")

        if self.turn_score >= 300 and (remaining_dice_count <= 2 or self.turn_score >= 500):
            Clock.schedule_once(lambda dt: self._bank_points(), 1.0)
        else:
            self._update_dice_styles()
            self.has_rolled_in_step = False
            Clock.schedule_once(lambda dt: self._roll_dice(), 1.2)


if __name__ == "__main__":
    DiceGameApp().run()
