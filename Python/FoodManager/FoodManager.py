import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import csv
import random
import os

# Ruta del archivo CSV
CSV_PATH = 'C:/Users/jaime/Desktop/Aprendiendo Python/comidas.csv'

# Función para añadir comida al CSV
def añadir_comida():
    comida = entrada_comida.get()
    categoria = categoria_var.get()

    if comida == "":
        mensaje_label.config(text="El nombre de la comida no puede estar vacío.", fg="red")
        return

    comida_existe = False
    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as archivo:
            lector = csv.reader(archivo)
            for fila in lector:
                if fila[0].lower() == comida.lower():
                    comida_existe = True
                    break
    except FileNotFoundError:
        pass

    if comida_existe:
        mensaje_label.config(text="La comida ya existe en la base de datos.", fg="red")
        return

    with open(CSV_PATH, 'a', newline='', encoding='utf-8') as archivo:
        escritor = csv.writer(archivo, quoting=csv.QUOTE_ALL)
        escritor.writerow([comida, categoria])

    entrada_comida.delete(0, tk.END)
    mensaje_label.config(text="Comida añadida correctamente.", fg="green")

# Función para cargar todas las entradas del CSV como lista de tuplas (nombre, categoría)
def cargar_todas_las_comidas():
    comidas = []
    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as archivo:
            lector = csv.reader(archivo)
            comidas = [tuple(fila) for fila in lector]
    except FileNotFoundError:
        pass
    return comidas

# Función para cargar datos desde el archivo CSV (para la pestaña "Seleccionar Comida")
def cargar_datos():
    comidas_nacionales = []
    comidas_internacionales = []
    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as archivo:
            lector = csv.reader(archivo)
            for fila in lector:
                nombre, categoria = fila
                if categoria == 'nacional':
                    comidas_nacionales.append(nombre)
                elif categoria == 'internacional':
                    comidas_internacionales.append(nombre)
    except FileNotFoundError:
        pass
    return comidas_nacionales, comidas_internacionales

# Función para seleccionar una comida aleatoria
def seleccionar_comida(categoria):
    comidas_nacionales, comidas_internacionales = cargar_datos()
    if categoria == 'nacional':
        comida = random.choice(comidas_nacionales) if comidas_nacionales else "No hay comidas nacionales disponibles."
    elif categoria == 'internacional':
        comida = random.choice(comidas_internacionales) if comidas_internacionales else "No hay comidas internacionales disponibles."
    elif categoria == 'indiferente':
        todas_comidas = comidas_nacionales + comidas_internacionales
        comida = random.choice(todas_comidas) if todas_comidas else "No hay comidas disponibles."
    else:
        comida = "Categoría no válida."
    return comida

# Función para mostrar la comida aleatoria
def mostrar_comida():
    categoria = categoria_var_selector.get()
    comida = seleccionar_comida(categoria)
    resultado_label.config(text=comida, fg="blue")

# Función para buscar comidas (pestaña "Buscador")
def buscar_comida():
    texto_busqueda = entrada_busqueda.get().lower()
    categoria_busqueda = categoria_var_buscador.get()
    comidas_nacionales, comidas_internacionales = cargar_datos()
    
    resultados = []
    if categoria_busqueda == 'nacional':
        resultados = [comida for comida in comidas_nacionales if texto_busqueda in comida.lower()]
    elif categoria_busqueda == 'internacional':
        resultados = [comida for comida in comidas_internacionales if texto_busqueda in comida.lower()]
    elif categoria_busqueda == 'indiferente':
        todas_comidas = comidas_nacionales + comidas_internacionales
        resultados = [comida for comida in todas_comidas if texto_busqueda in comida.lower()]
    
    popup = tk.Toplevel(ventana)
    popup.title("Resultados de la Búsqueda")
    popup.geometry("300x400")
    popup.transient(ventana)
    popup.grab_set()
    
    frame_popup = tk.Frame(popup)
    frame_popup.pack(fill="both", expand=True, padx=10, pady=10)
    
    frame_popup.grid_rowconfigure(0, weight=1)
    frame_popup.grid_rowconfigure(1, weight=0)
    frame_popup.grid_columnconfigure(0, weight=1)
    
    resultado_text = ScrolledText(frame_popup, width=40, height=20, font=("Arial", 12))
    resultado_text.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
    
    if resultados:
        resultado_text.insert(tk.END, "\n".join(resultados))
        resultado_text.config(foreground="blue")
    else:
        resultado_text.insert(tk.END, "No se encontraron resultados.")
        resultado_text.config(foreground="red")
    
    resultado_text.config(state="disabled")
    
    boton_cerrar = tk.Button(frame_popup, text="Cerrar", command=popup.destroy)
    boton_cerrar.grid(row=1, column=0, pady=10)

# Función para guardar cambios en el CSV
def guardar_cambios(comidas):
    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as archivo:
        escritor = csv.writer(archivo, quoting=csv.QUOTE_ALL)
        escritor.writerows(comidas)

# Función para editar una entrada
def editar_entrada(nombre_original):
    comidas = cargar_todas_las_comidas()
    comida_actual = next((c for c in comidas if c[0] == nombre_original), None)
    
    if not comida_actual:
        return
    
    popup_editar = tk.Toplevel(ventana)
    popup_editar.title(f"Editar: {nombre_original}")
    popup_editar.geometry("300x250")
    popup_editar.transient(ventana)
    popup_editar.grab_set()
    
    frame_editar = tk.Frame(popup_editar)
    frame_editar.pack(padx=10, pady=10, fill="both", expand=True)
    
    tk.Label(frame_editar, text="Nombre:").pack(pady=5)
    entrada_nombre = tk.Entry(frame_editar, width=30)
    entrada_nombre.insert(0, comida_actual[0])
    entrada_nombre.pack(pady=5)
    
    tk.Label(frame_editar, text="Categoría:").pack(pady=5)
    categoria_var_editar = tk.StringVar(value=comida_actual[1])
    tk.Radiobutton(frame_editar, text="Nacional", variable=categoria_var_editar, value="nacional").pack(pady=5)
    tk.Radiobutton(frame_editar, text="Internacional", variable=categoria_var_editar, value="internacional").pack(pady=5)
    
    def guardar():
        nuevo_nombre = entrada_nombre.get()
        nueva_categoria = categoria_var_editar.get()
        
        if not nuevo_nombre:
            messagebox.showerror("Error", "El nombre no puede estar vacío.")
            return
        
        comidas_actualizadas = [c for c in comidas if c[0] != nombre_original]
        if any(c[0].lower() == nuevo_nombre.lower() for c in comidas_actualizadas) and nuevo_nombre.lower() != nombre_original.lower():
            messagebox.showerror("Error", "Ya existe una comida con ese nombre.")
            return
        
        comidas_actualizadas.append((nuevo_nombre, nueva_categoria))
        guardar_cambios(comidas_actualizadas)
        messagebox.showinfo("Éxito", "Entrada actualizada correctamente.")
        popup_editar.destroy()
    
    def eliminar():
        if messagebox.askyesno("Confirmar", "¿Estás seguro de que quieres eliminar esta entrada?"):
            comidas_actualizadas = [c for c in comidas if c[0] != nombre_original]
            guardar_cambios(comidas_actualizadas)
            messagebox.showinfo("Éxito", "Entrada eliminada correctamente.")
            popup_editar.destroy()
    
    tk.Button(frame_editar, text="Guardar Cambios", command=guardar).pack(pady=10)
    tk.Button(frame_editar, text="Eliminar", command=eliminar).pack(pady=5)
    tk.Button(frame_editar, text="Cancelar", command=popup_editar.destroy).pack(pady=5)

# Función para buscar comidas en la pestaña "Editor"
def buscar_comida_editor():
    texto_busqueda = entrada_busqueda_editor.get().lower()
    comidas = cargar_todas_las_comidas()
    
    resultados = [comida[0] for comida in comidas if texto_busqueda in comida[0].lower()]
    
    popup = tk.Toplevel(ventana)
    popup.title("Resultados de la Búsqueda")
    popup.geometry("300x400")
    popup.transient(ventana)
    popup.grab_set()
    
    frame_popup = tk.Frame(popup)
    frame_popup.pack(fill="both", expand=True, padx=10, pady=10)
    
    canvas = tk.Canvas(frame_popup)
    scrollbar = tk.Scrollbar(frame_popup, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    
    if resultados:
        for resultado in resultados:
            btn = tk.Button(scrollable_frame, text=resultado, command=lambda r=resultado: editar_entrada(r), anchor="w", relief="flat", bg="white", fg="blue")
            btn.pack(fill="x", pady=2)
    else:
        tk.Label(scrollable_frame, text="No se encontraron resultados.", fg="red").pack(pady=10)
    
    tk.Button(frame_popup, text="Cerrar", command=popup.destroy).pack(pady=10)

# Crear la ventana principal
ventana = tk.Tk()
ventana.title("Gestión de Comidas")
ventana.geometry("500x400")

# Crear un widget de pestañas
tabs = ttk.Notebook(ventana)
tabs.pack(expand=1, fill="both")

# Crear las pestañas
frame_añadir = ttk.Frame(tabs)
frame_seleccionar = ttk.Frame(tabs)
frame_buscar = ttk.Frame(tabs)
frame_editor = ttk.Frame(tabs)  # Nueva pestaña "Editor"

tabs.add(frame_añadir, text="Añadir Comida")
tabs.add(frame_seleccionar, text="Seleccionar Comida")
tabs.add(frame_buscar, text="Buscador")
tabs.add(frame_editor, text="Editor")

# Contenido de la pestaña "Añadir Comida"
titulo_añadir = tk.Label(frame_añadir, text="Añadir Comida", font=("Arial", 16))
titulo_añadir.pack(pady=10)

label_comida = tk.Label(frame_añadir, text="Nombre de la comida:")
label_comida.pack(pady=5)
entrada_comida = tk.Entry(frame_añadir, width=40)
entrada_comida.pack(pady=5)

label_categoria = tk.Label(frame_añadir, text="Selecciona la categoría:")
label_categoria.pack(pady=5)

categoria_var = tk.StringVar(value="nacional")
radio_nacional = tk.Radiobutton(frame_añadir, text="Nacional", variable=categoria_var, value="nacional")
radio_nacional.pack(pady=5)
radio_internacional = tk.Radiobutton(frame_añadir, text="Internacional", variable=categoria_var, value="internacional")
radio_internacional.pack(pady=5)

boton_agregar = tk.Button(frame_añadir, text="Añadir Comida", command=añadir_comida)
boton_agregar.pack(pady=20)

mensaje_label = tk.Label(frame_añadir, text="", font=("Arial", 12))
mensaje_label.pack(pady=5)

# Contenido de la pestaña "Seleccionar Comida"
titulo_seleccionar = tk.Label(frame_seleccionar, text="Seleccionar Comida Aleatoria", font=("Arial", 16))
titulo_seleccionar.pack(pady=10)

categoria_var_selector = tk.StringVar(value="nacional")
radio_nacional_selector = tk.Radiobutton(frame_seleccionar, text="Nacional", variable=categoria_var_selector, value="nacional")
radio_nacional_selector.pack(pady=5)
radio_internacional_selector = tk.Radiobutton(frame_seleccionar, text="Internacional", variable=categoria_var_selector, value="internacional")
radio_internacional_selector.pack(pady=5)
radio_indiferente_selector = tk.Radiobutton(frame_seleccionar, text="Indiferente", variable=categoria_var_selector, value="indiferente")
radio_indiferente_selector.pack(pady=5)

boton_mostrar = tk.Button(frame_seleccionar, text="Comida Aleatoria", command=mostrar_comida)
boton_mostrar.pack(pady=20)

resultado_label = tk.Label(frame_seleccionar, text="", font=("Arial", 12))
resultado_label.pack(pady=5)

# Contenido de la pestaña "Buscador"
titulo_buscar = tk.Label(frame_buscar, text="Buscador de Comidas", font=("Arial", 16))
titulo_buscar.pack(pady=10)

label_busqueda = tk.Label(frame_buscar, text="Buscar comida:")
label_busqueda.pack(pady=5)
entrada_busqueda = tk.Entry(frame_buscar, width=40)
entrada_busqueda.pack(pady=5)

label_categoria_buscar = tk.Label(frame_buscar, text="Filtrar por categoría:")
label_categoria_buscar.pack(pady=5)

categoria_var_buscador = tk.StringVar(value="indiferente")
radio_nacional_buscar = tk.Radiobutton(frame_buscar, text="Nacional", variable=categoria_var_buscador, value="nacional")
radio_nacional_buscar.pack(pady=5)
radio_internacional_buscar = tk.Radiobutton(frame_buscar, text="Internacional", variable=categoria_var_buscador, value="internacional")
radio_internacional_buscar.pack(pady=5)
radio_indiferente_buscar = tk.Radiobutton(frame_buscar, text="Indiferente", variable=categoria_var_buscador, value="indiferente")
radio_indiferente_buscar.pack(pady=5)

boton_buscar = tk.Button(frame_buscar, text="Buscar", command=buscar_comida)
boton_buscar.pack(pady=20)

# Contenido de la pestaña "Editor"
titulo_editor = tk.Label(frame_editor, text="Editor de Comidas", font=("Arial", 16))
titulo_editor.pack(pady=10)

label_busqueda_editor = tk.Label(frame_editor, text="Buscar comida para editar:")
label_busqueda_editor.pack(pady=5)
entrada_busqueda_editor = tk.Entry(frame_editor, width=40)
entrada_busqueda_editor.pack(pady=5)

boton_buscar_editor = tk.Button(frame_editor, text="Buscar", command=buscar_comida_editor)
boton_buscar_editor.pack(pady=20)

# Iniciar la aplicación
ventana.mainloop()