import csv
import math
import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from collections import OrderedDict

def detect_encoding(filename):
    """Try common encodings to read the file."""
    encodings = ['utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
    for enc in encodings:
        try:
            with open(filename, 'r', encoding=enc) as f:
                f.read(1024) # try reading first bytes
            return enc
        except UnicodeDecodeError:
            continue
    return 'latin-1' # fallback

def read_csv(filename, log_callback=print):
    """Read CSV file with automatic encoding detection."""
    encoding = detect_encoding(filename)
    log_callback(f"Usando codificación: {encoding}")
    
    edges = []
    with open(filename, 'r', newline='', encoding=encoding) as f:
        reader = csv.reader(f)
        header = next(reader, None)
        
        if header and all(k in [col.lower() for col in header] for k in ['source', 'target', 'weight']):
            col_map = {col.lower(): idx for idx, col in enumerate(header)}
            for row in reader:
                if len(row) <= max(col_map['source'], col_map['target'], col_map['weight']):
                    continue
                try:
                    src = row[col_map['source']].strip()
                    tgt = row[col_map['target']].strip()
                    w = float(row[col_map['weight']])
                    edges.append((src, tgt, w))
                except ValueError:
                    continue
        else:
            # Fallback a asunción por posición (columnas 0, 1, 2)
            if header:
                try:
                    if len(header) >= 3:
                        edges.append((header[0].strip(), header[1].strip(), float(header[2])))
                except ValueError:
                    pass
            for row in reader:
                if len(row) < 3:
                    continue
                try:
                    src = row[0].strip()
                    tgt = row[1].strip()
                    w = float(row[2])
                    edges.append((src, tgt, w))
                except ValueError:
                    continue
    return edges

def get_unique_vertices(edges):
    """Return ordered list of unique vertex labels."""
    vertices = OrderedDict()
    for src, tgt, _ in edges:
        vertices[src] = None
        vertices[tgt] = None
    return list(vertices.keys())

def circular_coordinates(n, radius=1.0):
    """Generate (x, y, z=0) coordinates for n points on a circle."""
    coords = []
    for i in range(n):
        angle = 2 * math.pi * i / n
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        coords.append((x, y, 0.0))
    return coords

def write_net(filename, vertices, edges, directed=True):
    """Write Pajek .net file with circular coordinates."""
    n = len(vertices)
    coords = circular_coordinates(n)
    vertex_id_map = {v: idx for idx, v in enumerate(vertices, start=1)}
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"*Vertices {n}\n")
        for label, (x, y, z) in zip(vertices, coords):
            v_id = vertex_id_map[label]
            safe_label = label.replace('"', "'")
            f.write(f'{v_id} "{safe_label}" {x:.6f} {y:.6f} {z:.6f}\n')
            
        if directed:
            f.write("*Arcs\n")
        else:
            f.write("*Edges\n")
            
        for src, tgt, w in edges:
            src_id = vertex_id_map[src]
            tgt_id = vertex_id_map[tgt]
            f.write(f'{src_id} {tgt_id} {w:.6f}\n')

class CsvToPajekApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Conversor CSV a Pajek (.net)")
        self.root.geometry("600x450")
        self.root.resizable(False, False)
        
        self.input_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.is_directed = tk.BooleanVar(value=True) # Por defecto Dirigido
        
        self.create_widgets()

    def create_widgets(self):
        # --- Frame de Entrada ---
        frame_in = tk.LabelFrame(self.root, text="1. Archivo de Entrada (CSV)", padx=10, pady=10)
        frame_in.pack(fill="x", padx=10, pady=5)
        
        tk.Entry(frame_in, textvariable=self.input_file, state='readonly', width=65).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(frame_in, text="Explorar...", command=self.select_input).pack(side=tk.LEFT)

        # --- Frame de Salida ---
        frame_out = tk.LabelFrame(self.root, text="2. Archivo de Salida (.net)", padx=10, pady=10)
        frame_out.pack(fill="x", padx=10, pady=5)
        
        tk.Entry(frame_out, textvariable=self.output_file, state='readonly', width=65).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(frame_out, text="Guardar como...", command=self.select_output).pack(side=tk.LEFT)

        # --- Frame de Opciones ---
        frame_opts = tk.Frame(self.root, padx=10, pady=10)
        frame_opts.pack(fill="x")
        
        tk.Checkbutton(frame_opts, text="Grafo Dirigido (Arcs)", variable=self.is_directed).pack(side=tk.LEFT)

        # --- Botón de Procesamiento ---
        tk.Button(self.root, text="Convertir a Pajek", font=("Arial", 12, "bold"), bg="#4CAF50", fg="white", 
                  command=self.process_conversion).pack(pady=10)

        # --- Consola de Log ---
        tk.Label(self.root, text="Registro de procesos:").pack(anchor="w", padx=10)
        self.log_text = scrolledtext.ScrolledText(self.root, height=10, state='disabled', bg="#f4f4f4")
        self.log_text.pack(fill="x", padx=10, pady=(0, 10))

    def log(self, message):
        """Añade un mensaje a la consola de texto de la interfaz."""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def select_input(self):
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo CSV",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
        )
        if filename:
            self.input_file.set(filename)
            # Sugerir un nombre de salida automáticamente
            base = os.path.splitext(filename)[0]
            self.output_file.set(base + ".net")

    def select_output(self):
        filename = filedialog.asksaveasfilename(
            title="Guardar archivo Pajek como",
            defaultextension=".net",
            filetypes=[("Archivos Pajek", "*.net"), ("Todos los archivos", "*.*")]
        )
        if filename:
            self.output_file.set(filename)

    def process_conversion(self):
        input_csv = self.input_file.get()
        output_net = self.output_file.get()
        directed = self.is_directed.get()
        
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END) # Limpiar log
        self.log_text.config(state='disabled')

        if not input_csv or not output_net:
            messagebox.showwarning("Faltan datos", "Por favor, seleccione tanto el archivo de entrada como el de salida.")
            return

        try:
            self.log(f"Leyendo {os.path.basename(input_csv)}...")
            edges = read_csv(input_csv, log_callback=self.log)
            
            if not edges:
                self.log("ERROR: No se encontraron aristas válidas en el archivo.")
                messagebox.showerror("Error", "El archivo CSV está vacío o no tiene el formato correcto (source, target, weight).")
                return

            vertices = get_unique_vertices(edges)
            self.log(f"Generando red con {len(vertices)} vértices y {len(edges)} aristas...")
            
            write_net(output_net, vertices, edges, directed=directed)
            
            self.log(f"¡Éxito! Archivo guardado en:\n{output_net}")
            messagebox.showinfo("Proceso Completado", f"Se ha generado el archivo .net exitosamente con {len(vertices)} nodos.")

        except FileNotFoundError:
            self.log(f"ERROR: No se encontró el archivo '{input_csv}'.")
            messagebox.showerror("Error de Archivo", "No se pudo encontrar el archivo CSV especificado.")
        except Exception as e:
            self.log(f"Error inesperado: {e}")
            messagebox.showerror("Error", f"Ha ocurrido un error:\n{str(e)}")

if __name__ == '__main__':
    root = tk.Tk()
    app = CsvToPajekApp(root)
    root.mainloop()