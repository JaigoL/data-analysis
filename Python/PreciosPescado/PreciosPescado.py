import xlrd
import tkinter as tk
from tkinter import ttk, messagebox

#URL del lugar dónde se obtiene el archivo de Excel: https://www.mercamadrid.es/estadisticas/
# Ruta absoluta al archivo de Excel
archivo_excel = r"C:\Users\jaime\Desktop\Aprendiendo Python\PreciosPescado\Estadisticas.xls"

# Crear ventana principal
root = tk.Tk()
root.title("Buscador de precios")
root.geometry("400x300")

notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill='both')

# Mapeo de categorías
familia_map = {
    "Pescado fresco": "PESC.FRESCO",
    "Congelados": "CONGELADOS",
    "Marisco fresco": "MARISCO FR."
}

# --- Primera pestaña: Cargar datos ---
def cargar_datos():
    try:
        familia_elegida = familia_map[familia_var.get()]
        num_entradas = int(num_entradas_var.get())

        if num_entradas <= 0:
            messagebox.showerror("Error", "El número de entradas debe ser mayor que 0.")
            return

        workbook = xlrd.open_workbook(archivo_excel)
        sheet = workbook.sheet_by_index(0)
        headers = sheet.row_values(1)

        if "FAMILIA" not in headers or "Producto" not in headers or "Precio m?s frecuente ?/Kg" not in headers:
            messagebox.showerror("Error", "No se encontraron las columnas esperadas en el archivo.")
            return

        familia_idx = headers.index("FAMILIA")
        producto_idx = headers.index("Producto")
        precio_idx = headers.index("Precio m?s frecuente ?/Kg")

        productos = []
        for row_idx in range(2, sheet.nrows):
            row = sheet.row_values(row_idx)
            if row[familia_idx] == familia_elegida and row[precio_idx] != 0:
                productos.append((row[producto_idx], row[precio_idx]))

        productos_ordenados = sorted(productos, key=lambda x: x[1])
        productos_unicos = {}
        for producto, precio in productos_ordenados:
            if producto not in productos_unicos:
                productos_unicos[producto] = precio

        mostrar_popup(list(productos_unicos.items())[:num_entradas], ["Producto", "Precio"])
    except Exception as e:
        messagebox.showerror("Error", f"Hubo un error: {e}")

# --- Segunda pestaña: Búsqueda de productos ---
def buscar_datos():
    try:
        texto_busqueda = search_var.get().strip().lower()
        familia_elegida = familia_map[familia_var_busqueda.get()]

        workbook = xlrd.open_workbook(archivo_excel)
        sheet = workbook.sheet_by_index(0)
        headers = sheet.row_values(1)

        if "FAMILIA" not in headers or "Producto" not in headers or "Variedad" not in headers or "Precio m?s frecuente ?/Kg" not in headers:
            messagebox.showerror("Error", "No se encontraron las columnas esperadas en el archivo.")
            return

        familia_idx = headers.index("FAMILIA")
        producto_idx = headers.index("Producto")
        variedad_idx = headers.index("Variedad")
        precio_idx = headers.index("Precio m?s frecuente ?/Kg")

        resultados = []
        for row_idx in range(2, sheet.nrows):
            row = sheet.row_values(row_idx)
            if row[familia_idx] == familia_elegida and texto_busqueda in str(row[producto_idx]).lower():
                resultados.append((row[producto_idx], row[variedad_idx], row[precio_idx]))

        mostrar_popup(resultados, ["Producto", "Variedad", "Precio"])
    except Exception as e:
        messagebox.showerror("Error", f"Hubo un error: {e}")

# --- Función para mostrar los resultados en un popup ---
def mostrar_popup(resultados, headers):
    popup = tk.Toplevel(root)
    popup.title("Resultados")
    tree = ttk.Treeview(popup, columns=[str(i) for i in range(len(headers))], show='headings')
    
    for i, col in enumerate(headers):
        tree.heading(str(i), text=col)
    
    for res in resultados:
        tree.insert("", "end", values=res)
    
    tree.pack(padx=10, pady=10)

# --- Pestaña 1: Cargar Datos ---
pestana_cargar = ttk.Frame(notebook)
notebook.add(pestana_cargar, text="Más baratos")

familia_var = tk.StringVar()
ttk.Label(pestana_cargar, text="Selecciona categoría:").pack(pady=5)
familia_dropdown = ttk.Combobox(pestana_cargar, textvariable=familia_var, values=list(familia_map.keys()), state="readonly")
familia_dropdown.set("Pescado fresco")
familia_dropdown.pack()

num_entradas_var = tk.StringVar()
ttk.Label(pestana_cargar, text="Número de entradas:").pack(pady=5)
num_entradas_entry = tk.Entry(pestana_cargar, textvariable=num_entradas_var)
num_entradas_entry.pack()

ttk.Button(pestana_cargar, text="Cargar", command=cargar_datos).pack(pady=10)

# --- Pestaña 2: Búsqueda ---
pestana_buscar = ttk.Frame(notebook)
notebook.add(pestana_buscar, text="Buscar producto")

familia_var_busqueda = tk.StringVar()
ttk.Label(pestana_buscar, text="Selecciona categoría:").pack(pady=5)
familia_dropdown_busqueda = ttk.Combobox(pestana_buscar, textvariable=familia_var_busqueda, values=list(familia_map.keys()), state="readonly")
familia_dropdown_busqueda.set("Pescado fresco")
familia_dropdown_busqueda.pack()

search_var = tk.StringVar()
ttk.Label(pestana_buscar, text="Buscar producto:").pack(pady=5)
search_entry = tk.Entry(pestana_buscar, textvariable=search_var)
search_entry.pack()

ttk.Button(pestana_buscar, text="Buscar", command=buscar_datos).pack(pady=10)

root.mainloop()