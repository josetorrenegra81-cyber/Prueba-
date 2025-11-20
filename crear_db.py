import sqlite3

conn = sqlite3.connect("bot.db")
cursor = conn.cursor()

# Tabla de usuarios
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY,
    nombre TEXT,
    ultimo_test INTEGER,
    puntaje_total INTEGER DEFAULT 0,
    total_preguntas INTEGER DEFAULT 0
)
""")

# Tabla de preguntas
cursor.execute("""
CREATE TABLE IF NOT EXISTS preguntas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pregunta TEXT,
    respuesta TEXT
)
""")

# Tabla de evaluaciones
cursor.execute("""
CREATE TABLE IF NOT EXISTS evaluaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    puntaje INTEGER,
    fecha TEXT
)
""")

# Preguntas basado en Orange Freight
preguntas = [
    ("¿Qué hace Orange Freight?", 
     "Es una empresa logística dedicada al transporte internacional de carga y soluciones de freight forwarding."),

    ("¿Qué servicios ofrece Orange Freight?", 
     "Transporte aéreo, marítimo, terrestre, bodegaje, aduanas y soluciones logísticas integrales."),

    ("¿Cuál es la misión de la empresa?", 
     "Brindar soluciones logísticas eficientes y confiables para el comercio internacional."),

    ("¿Cuál es la visión de Orange Freight?", 
     "Ser líderes en logística internacional con innovación y excelencia."),

    ("¿Qué valores tiene la empresa?", 
     "Responsabilidad, confianza, eficiencia, integridad y compromiso."),

    ("¿Qué comercializa Orange Freight?", 
     "Servicios logísticos, transporte internacional y asesorías en comercio exterior.")
]

cursor.executemany("INSERT INTO preguntas (pregunta, respuesta) VALUES (?,?)", preguntas)

conn.commit()
conn.close()

print("Base de datos creada correctamente.")
