import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re
import csv
from collections import Counter
import os
import math
import time  # Para medir el tiempo de procesamiento

class WordFrequencyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Generador de Diccionario de Términos Excluidos (Optimizado)")
        self.root.geometry("750x750")
        self.filepath = None
        self.raw_text_original = ""   
        self.original_words_case = [] 
        self.case_map = {} # NUEVO: Caché para evitar congelamiento de Tkinter

        # ---------- Lista de stopwords en español ----------
        self.stopwords = self._load_stopwords()

        # ---------- SECCIÓN 1: Selección de Archivo ----------
        frame_file = tk.LabelFrame(root, text="1. Archivo de Texto", padx=10, pady=10)
        frame_file.pack(padx=10, pady=10, fill="x")

        self.btn_select = tk.Button(frame_file, text="Seleccionar TXT", command=self.select_file)
        self.btn_select.grid(row=0, column=0, padx=5, pady=5)

        self.lbl_file = tk.Label(frame_file, text="Ningún archivo seleccionado", fg="gray")
        self.lbl_file.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # ---------- SECCIÓN 2: Parámetros de Calibración ----------
        frame_params = tk.LabelFrame(root, text="2. Parámetros de Calibración", padx=10, pady=10)
        frame_params.pack(padx=10, pady=10, fill="x")

        tk.Label(frame_params, text="Longitud mínima de palabra:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.entry_min_len = tk.Entry(frame_params, width=10)
        self.entry_min_len.insert(0, "3")
        self.entry_min_len.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        tk.Label(frame_params, text="Frecuencia mínima (absoluta):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.entry_min_freq = tk.Entry(frame_params, width=10)
        self.entry_min_freq.insert(0, "15")
        self.entry_min_freq.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        tk.Label(frame_params, text="Umbral relativo (%):").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.entry_rel_threshold = tk.Entry(frame_params, width=10)
        self.entry_rel_threshold.insert(0, "0.5")   
        self.entry_rel_threshold.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        tk.Label(frame_params, text="Límite (Top N palabras):").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.entry_top_n = tk.Entry(frame_params, width=10)
        self.entry_top_n.insert(0, "100")
        self.entry_top_n.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        self.var_stopwords_only = tk.BooleanVar(value=False)
        chk_stopwords = tk.Checkbutton(frame_params, text="Solo palabras vacías (stopwords)", 
                                       variable=self.var_stopwords_only)
        chk_stopwords.grid(row=4, column=0, columnspan=2, sticky="w", padx=20)

        self.var_exclude_proper = tk.BooleanVar(value=False)
        chk_proper = tk.Checkbutton(frame_params, text="Excluir nombres propios (siempre mayúscula inicial)", 
                                    variable=self.var_exclude_proper)
        chk_proper.grid(row=5, column=0, columnspan=2, sticky="w", padx=20)

        tk.Label(frame_params, text="Método de ordenamiento:").grid(row=6, column=0, padx=5, pady=5, sticky="e")
        self.combo_sort = ttk.Combobox(frame_params, values=["Frecuencia absoluta", "Frecuencia relativa", "Informatividad (log N/freq)"], 
                                       state="readonly", width=25)
        self.combo_sort.current(0)
        self.combo_sort.grid(row=6, column=1, padx=5, pady=5, sticky="w")

        self.btn_process = tk.Button(frame_params, text="Procesar y Mostrar Resultados", command=self.process_text, bg="#d9edf7")
        self.btn_process.grid(row=7, column=0, columnspan=2, pady=10)

        # ---------- SECCIÓN 3: Resultados ----------
        frame_results = tk.LabelFrame(root, text="3. Resultados (seleccione filas y presione 'Eliminar selección')", padx=10, pady=10)
        frame_results.pack(padx=10, pady=10, fill="both", expand=True)

        self.tree = ttk.Treeview(frame_results, columns=("Palabra", "Frecuencia", "Relativa(%)"), show="headings", height=12)
        self.tree.heading("Palabra", text="Palabra")
        self.tree.heading("Frecuencia", text="Frecuencia Abs.")
        self.tree.heading("Relativa(%)", text="Frec. Relativa (%)")
        self.tree.column("Palabra", width=200, anchor="center")
        self.tree.column("Frecuencia", width=120, anchor="center")
        self.tree.column("Relativa(%)", width=120, anchor="center")

        scrollbar = ttk.Scrollbar(frame_results, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        frame_buttons = tk.Frame(frame_results)
        frame_buttons.pack(fill="x", pady=5)

        self.btn_delete = tk.Button(frame_buttons, text="Eliminar selección", command=self.delete_selected, bg="#f0ad4e")
        self.btn_delete.pack(side="left", padx=5)

        self.btn_export = tk.Button(frame_buttons, text="Exportar a CSV (lista actual)", command=self.export_current_list, bg="#5bc0de")
        self.btn_export.pack(side="left", padx=5)

        self.btn_reset = tk.Button(frame_buttons, text="Restablecer resultados originales", command=self.reset_to_original, bg="#d9534f", fg="white")
        self.btn_reset.pack(side="left", padx=5)

        self.original_results = []   

    def _load_stopwords(self):
        return set([
            "un", "una", "unos", "unas", "el", "la", "los", "las", "y", "o", "u", "pero", "sin", "sobre",
            "que", "es", "son", "fue", "fueron", "ser", "estar", "para", "por", "con", "de", "en", "a",
            "al", "del", "lo", "le", "les", "se", "me", "te", "nos", "os", "mi", "tu", "su", "nuestro",
            "vuestro", "este", "esta", "estos", "estas", "aquel", "aquella", "aquellos", "aquellas",
            "muy", "más", "menos", "tan", "tanto", "como", "cuando", "donde", "cual", "cuales", "quien",
            "quienes", "durante", "mediante", "según", "entre", "hacia", "hasta", "desde", "contra",
            "ante", "bajo", "cabe", "versus", "vía", "vs", "éste", "ésta", "aquélla", "aquéllos"
        ])

    def select_file(self):
        self.filepath = filedialog.askopenfilename(filetypes=[("Archivos de texto", "*.txt")])
        if self.filepath:
            self.lbl_file.config(text=os.path.basename(self.filepath), fg="black")

    def process_text(self):
        if not self.filepath:
            messagebox.showerror("Error", "Seleccione un archivo TXT primero.")
            return

        try:
            min_len = int(self.entry_min_len.get())
            min_freq_abs = int(self.entry_min_freq.get())
            rel_threshold = float(self.entry_rel_threshold.get())
            top_n = int(self.entry_top_n.get())
            if min_len < 1 or min_freq_abs < 0 or rel_threshold < 0 or top_n < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Parámetros inválidos. Use números enteros positivos (y relativo ≥ 0).")
            return

        # Iniciar medición de tiempo
        start_time = time.time()

        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.raw_text_original = f.read()

            self.original_words_case = re.findall(r'\b[A-Za-zÁÉÍÓÚÑÜáéíóúñü]+\b', self.raw_text_original)

            # NUEVO: Generar mapa (Hash Map en O(1)) para consulta inmediata de mayúsculas
            self.case_map = {}
            for w in self.original_words_case:
                w_lower = w.lower()
                if w_lower not in self.case_map:
                    self.case_map[w_lower] = []
                self.case_map[w_lower].append(w)

            words_lower = [w.lower() for w in self.original_words_case]
            filtered_words = [w for w in words_lower if len(w) >= min_len]

            total_words = len(filtered_words)
            if total_words == 0:
                messagebox.showwarning("Sin palabras", "No se encontraron palabras que cumplan la longitud mínima.")
                return

            counter = Counter(filtered_words)
            candidates = []
            
            for word, freq_abs in counter.items():
                if freq_abs < min_freq_abs:
                    continue
                
                rel_freq = (freq_abs / total_words) * 100.0
                if rel_freq < rel_threshold:
                    continue

                if self.var_stopwords_only.get() and word not in self.stopwords:
                    continue

                if self.var_exclude_proper.get() and self._is_proper_noun(word):
                    continue

                candidates.append((word, freq_abs, rel_freq))

            sort_method = self.combo_sort.get()
            if sort_method == "Frecuencia relativa":
                candidates.sort(key=lambda x: x[2], reverse=True)
            elif sort_method == "Informatividad (log N/freq)":
                candidates.sort(key=lambda x: math.log(total_words / (x[1] + 1e-9)), reverse=False)
            else:  
                candidates.sort(key=lambda x: x[1], reverse=True)

            self.original_results = candidates[:top_n]
            self._populate_tree(self.original_results)

            elapsed_time = time.time() - start_time

            if not self.original_results:
                messagebox.showinfo("Sin resultados", "No hay palabras que cumplan todos los filtros. Ajuste los parámetros.")
            else:
                messagebox.showinfo("Completado", f"Se procesaron {total_words} palabras en {elapsed_time:.2f} segundos.\n\nEncontradas: {len(self.original_results)}.")

        except Exception as e:
            messagebox.showerror("Error", f"Fallo al procesar:\n{e}")

    def _is_proper_noun(self, word_lower):
        """
        Consulta O(1) usando el mapa de caché. Evita congelamiento de interfaz.
        """
        occurrences = self.case_map.get(word_lower, [])
        if not occurrences:
            return False
            
        proper_count = 0
        for occ in occurrences:
            if occ[0].isupper() and (len(occ) == 1 or occ[1:].islower()):
                proper_count += 1
                
        ratio = proper_count / len(occurrences)
        return ratio > 0.9

    def _populate_tree(self, data):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for word, freq_abs, freq_rel in data:
            self.tree.insert("", "end", values=(word, freq_abs, f"{freq_rel:.2f}"))

    def delete_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("Sin selección", "Seleccione una o más filas para eliminar.")
            return
        for item in selected_items:
            self.tree.delete(item)

    def export_current_list(self):
        if not self.tree.get_children():
            messagebox.showwarning("Lista vacía", "No hay datos para exportar.")
            return

        if self.filepath:
            base = os.path.splitext(self.filepath)[0]
            out_path = base + "_diccionario_excluidos.csv"
        else:
            out_path = "diccionario_excluidos.csv"

        try:
            with open(out_path, 'w', encoding='utf-8-sig', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Palabra_Excluida", "Frecuencia_Absoluta", "Frecuencia_Relativa(%)"])
                for item in self.tree.get_children():
                    values = self.tree.item(item)["values"]
                    # CORRECCIÓN DE BUG: Evitar atributo `replace` sobre floats. Se formatea como str.
                    writer.writerow([values[0], values[1], str(values[2])]) 
            messagebox.showinfo("Éxito", f"Archivo guardado en:\n{out_path}")
        except Exception as e:
            messagebox.showerror("Error de exportación", str(e))

    def reset_to_original(self):
        if self.original_results:
            self._populate_tree(self.original_results)
            messagebox.showinfo("Restaurado", "Se han recuperado los resultados originales.")
        else:
            messagebox.showwarning("Sin datos", "No hay resultados originales. Procese un archivo primero.")

if __name__ == "__main__":
    root = tk.Tk()
    app = WordFrequencyApp(root)
    root.mainloop()