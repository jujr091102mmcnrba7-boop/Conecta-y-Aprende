from flask import Flask, render_template, request, redirect, url_for, abort, session, flash
from pymongo import MongoClient, ReturnDocument
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
import os
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "static", "uploads")
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif"}
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
client = MongoClient(app.config["MONGO_URI"])
db = client[app.config["MONGO_DB"]]

ROLE_LABELS = {
    "admin": "Administrador",
    "instructor": "Instructor",
    "docente": "Docente",
    "alumno": "Alumno",
    "recuperacion": "Persona en Recuperación"
}

INSTRUCTOR_EMAIL_SUFFIX = "@instructores.conecta"

ROLE_PAGES = {
    "admin": [1, 2, 3, 4, 5, 6, 7, 8, 9],
    "instructor": [1, 2, 3, 4, 5, 6, 7, 9],
    "docente": [1, 2, 3, 4, 5, 6, 7, 9],
    "alumno": [1, 2, 3, 4, 5, 6, 7, 9],
    "recuperacion": [1, 2, 3, 4, 5, 6, 7, 9]
}

PAGE_TITLES = {
    1: "Bienvenida",
    2: "Tipos de Usuarios",
    3: "Funcionalidades",
    4: "Niveles de Aprendizaje",
    5: "Cronograma",
    6: "Tu Futuro",
    7: "Mi Perfil",
    8: "Panel Admin",
    9: "Actividades"
}

PAGE_TEMPLATES = {
    1: "interface1.html",
    2: "interface2.html",
    3: "interface3.html",
    4: "interface4.html",
    5: "interface5.html",
    6: "interface6.html",
    7: "interface7.html",
    8: "interface8.html",
    9: "interface9.html",
}

PAGE_SUMMARIES = {
    1: "Inicio del programa con opciones concretas para tu rol.",
    2: "Entiende cómo cada participante contribuye a la comunidad de recuperación.",
    3: "Funcionalidades diseñadas para tu aprendizaje, apoyo y seguimiento.",
    4: "Rutas de formación específicas según tu perfil y etapa.",
    5: "Fechas y pasos clave de tu proceso educativo y de reintegración.",
    6: "Oportunidades para mejorar tus habilidades y tu camino al empleo.",
    7: "Actualiza tu información y revisa tu estado en el programa.",
    8: "Herramientas administrativas para supervisar la comunidad y el avance.",
    9: "Actividades y apoyos disponibles según tu rol y necesidades.",
}

ROLE_HOME_MESSAGE = {
    "admin": "Accede al panel de administración, revisa usuarios y configura el proyecto desde tu espacio.",
    "instructor": "Encuentra tus recursos de formación, talleres y el control de tus grupos de aprendizaje.",
    "docente": "Encuentra tus recursos de apoyo y el seguimiento de tus grupos.",
    "alumno": "Descubre los módulos recomendados, tus actividades y tu progreso personal.",
    "recuperacion": "Visualiza tu plan de recuperación, actividades y apoyo personalizado para avanzar.",
}

ROLE_ACTIONS = {
    "admin": [
        {"label": "Mi Perfil", "endpoint": "profile"},
        {"label": "Panel Admin", "endpoint": "admin_users"},
        {"label": "Actividades", "endpoint": "actividades_disponibles"},
        {"label": "Solicitudes", "endpoint": "admin_activity_requests"},
        {"label": "Transferencias", "endpoint": "admin_cash_transfers"},
        {"label": "Préstamos", "endpoint": "admin_loans"},
        {"label": "Historial", "endpoint": "admin_action_history"},
    ],
    "instructor": [
        {"label": "Mi Perfil", "endpoint": "profile"},
        {"label": "Panel Instructor", "endpoint": "instructor_dashboard"},
        {"label": "Mis Estudiantes", "endpoint": "instructor_students"},
        {"label": "Talleres", "endpoint": "instructor_workshops"},
        {"label": "Recursos", "endpoint": "instructor_resources"},
        {"label": "Evidencias", "endpoint": "instructor_evidences"},
    ],
    "docente": [
        {"label": "Mi Perfil", "endpoint": "profile"},
        {"label": "Actividades", "endpoint": "actividades_disponibles"},
        {"label": "Mi Actividad", "endpoint": "user_activity_dashboard"},
        {"label": "Certificados", "endpoint": "certificados"},
    ],
    "alumno": [
        {"label": "Mi Perfil", "endpoint": "profile"},
        {"label": "Actividades", "endpoint": "actividades_disponibles"},
        {"label": "Mi Actividad", "endpoint": "user_activity_dashboard"},
        {"label": "Certificados", "endpoint": "certificados"},
    ],
    "recuperacion": [
        {"label": "Mi Perfil", "endpoint": "profile"},
        {"label": "Actividades", "endpoint": "actividades_disponibles"},
        {"label": "Mi Actividad", "endpoint": "user_activity_dashboard"},
        {"label": "Contacto", "endpoint": "contact"},
    ],
}

ACTIVITY_OPTIONS = [
    {
        "name": "Reparación de Herrería",
        "info": "Actividad práctica de herrería con orientación técnica. No tiene costo y permite aprender trabajos en metal y estructuras.",
        "cost": 0,
    },
    {
        "name": "Instalación de Redes",
        "info": "Trabajo técnico de instalación y mantenimiento de redes básicas. Incluye revisión de cableado y configuración de equipos.",
        "cost": 80,
    },
    {
        "name": "Diseño Gráfico",
        "info": "Creación de materiales visuales y apoyo en proyectos creativos. Ideal para usuarios con interés en comunicación y creatividad.",
        "cost": 100,
    },
    {
        "name": "Oficio de Mecánica",
        "info": "Actividad complementaria con pago reducido para quienes deseen aprender mecánica básica y reparación de vehículo ligero.",
        "cost": 120,
    },
    {
        "name": "Oficio de Carpintería",
        "info": "Actividad complementaria sin costo para quienes quieran practicar corte, ensamblaje y técnicas básicas de carpintería.",
        "cost": 0,
    },
    {
        "name": "Oficio de Costura",
        "info": "Actividad complementaria sin costo para quienes deseen aprender costura básica, confección y reparación textil.",
        "cost": 0,
    },
]

PAGE_INFO = {
    1: {
        "subtitle": "Tu punto de partida en el programa Conecta y Aprende.",
        "points": [
            "Accede a tu ruta de formación y apoyo social.",
            "Encuentra las áreas que te corresponden según tu rol.",
            "Conoce el propósito de la plataforma para la recuperación.",
        ],
        "resources": [
            {"title": "Videos introductorios", "description": "Presentaciones en video sobre el proyecto, la misión y los primeros pasos en el sistema.", "image": "video.svg"},
            {"title": "Infografías clave", "description": "Esquemas visuales sobre la estructura del sitio y el apoyo para personas en rehabilitación.", "image": "infographic.svg"},
            {"title": "Guías de estudio", "description": "Materiales fáciles de seguir para comenzar en las áreas de educación digital, cultura y oficios.", "image": "guide.svg"},
            {"title": "Glosario básico", "description": "Términos clave relacionados con la plataforma y los objetivos de la intervención educativa.", "image": "glossary.svg"},
        ],
        "features": [
            {"title": "Inicio enfocado", "description": "Solo se muestra información útil para ti."},
            {"title": "Apoyo claro", "description": "Orientación en cada paso de tu proceso."},
        ],
        "secondary_action": {"label": "Ver detalles del programa", "endpoint": "home"},
    },
    2: {
        "subtitle": "Conoce cómo colabora cada perfil en la recuperación y educación.",
        "points": [
            "Admin: gestiona usuarios, activaciones y seguimiento del proyecto.",
            "Docente: diseña actividades y brinda acompañamiento educativo.",
            "Alumno: aplica nuevas habilidades y accede al apoyo dirigido.",
            "Recuperación: recibe acompañamiento para tu reinserción social.",
        ],
        "resources": [
            {"title": "Manual de roles", "description": "Documento de usuario para entender responsabilidades y accesos en la plataforma.", "image": "guide.svg"},
            {"title": "Presentaciones para equipos", "description": "Diapositivas sobre los perfiles, la participación y el impacto esperado.", "image": "presentation.svg"},
            {"title": "Lecturas de apoyo", "description": "Artículos breves sobre inclusión social, rehabilitación y trabajo comunitario.", "image": "glossary.svg"},
            {"title": "Infografías de roles", "description": "Material visual que explica a cada usuario lo que debe hacer y cómo aportar al proyecto.", "image": "infographic.svg"},
        ],
        "features": [
            {"title": "Roles con sentido", "description": "Cada usuario aporta a la comunidad educativa y de apoyo."},
            {"title": "Acceso responsable", "description": "Solo tienes acceso a lo que necesitas."},
        ],
    },
    3: {
        "subtitle": "Descubre las funcionalidades diseñadas para tu desarrollo.",
        "points": [
            "Seguimiento de actividades y avances.",
            "Gestión de solicitudes y validaciones.",
            "Recursos de apoyo y formación práctica.",
        ],
        "resources": [
            {"title": "Cuestionarios y quizzes", "description": "Pruebas sencillas para consolidar aprendizajes y medir tu progreso.", "image": "quiz.svg"},
            {"title": "Videos de orientación", "description": "Guías en video que muestran cómo usar el sitio y aprovechar cada sección.", "image": "video.svg"},
            {"title": "Artículos de apoyo", "description": "Documentos con consejos prácticos para docentes, estudiantes y participantes en recuperación.", "image": "guide.svg"},
            {"title": "Mapas conceptuales", "description": "Esquemas para comprender la relación entre todas las funciones del sistema.", "image": "infographic.svg"},
        ],
        "features": [
            {"title": "Práctico", "description": "Funcionalidades relacionadas con tu recuperación y aprendizaje."},
            {"title": "Personalizado", "description": "Cada rol encuentra solo lo que le corresponde."},
        ],
    },
    4: {
        "subtitle": "Tu ruta de aprendizaje dentro del proyecto.",
        "points": [
            "Cursos y talleres enfocados en oficios, creatividad y digitalización.",
            "Recursos para docentes y facilitadores.",
            "Acompañamiento para la transición hacia una nueva etapa.",
        ],
        "resources": [
            {"title": "Mapas conceptuales", "description": "Organiza el aprendizaje por niveles y temas con esquemas claros.", "image": "infographic.svg"},
            {"title": "Presentaciones de avance", "description": "Diapositivas breves para entender el contenido de cada nivel.", "image": "presentation.svg"},
            {"title": "Guías de estudio", "description": "Materiales paso a paso para avanzar en las competencias digitales y de oficio.", "image": "guide.svg"},
            {"title": "Videos de cada módulo", "description": "Lecciones audiovisuales que acompañan el progreso en tiempo real.", "image": "video.svg"},
        ],
        "features": [
            {"title": "Aprendizaje guiado", "description": "Contenidos que conectan con tus objetivos."},
            {"title": "Avance paso a paso", "description": "Información presentada de forma clara y directa."},
        ],
    },
    5: {
        "subtitle": "Planifica tu participación y mantente al día.",
        "points": [
            "Fechas de talleres y sesiones formativas.",
            "Plazos para actividades y seguimiento.",
            "Eventos de acompañamiento y evaluación.",
        ],
        "resources": [
            {"title": "Video del cronograma", "description": "Explicación visual de las fases del proyecto y fechas clave.", "image": "video.svg"},
            {"title": "Infografías de fases", "description": "Representaciones gráficas de la ruta de 4 meses y sus objetivos.", "image": "infographic.svg"},
            {"title": "Documentos de planificación", "description": "Archivos con detalles de cada etapa y los compromisos esperados.", "image": "guide.svg"},
            {"title": "Manual de uso", "description": "Guía para entender cómo consultar el cronograma y participar en los eventos.", "image": "guide.svg"},
        ],
        "features": [
            {"title": "Agenda útil", "description": "Solo muestra lo que realmente importa."},
            {"title": "Organización efectiva", "description": "Te ayuda a cumplir con tu plan."},
        ],
    },
    6: {
        "subtitle": "Explora tus metas profesionales y sociales.",
        "points": [
            "Oportunidades de empleo y capacitación.",
            "Rutas para mejorar tus habilidades digitales o de oficio.",
            "Apoyo para tu inserción laboral o educativa.",
        ],
        "resources": [
            {"title": "Presentaciones de oportunidades", "description": "Diapositivas con caminos de empleo, emprendimiento y crecimiento personal.", "image": "presentation.svg"},
            {"title": "Artículos y lecturas", "description": "Textos sobre trabajo, emprendimiento y superación personal.", "image": "guide.svg"},
            {"title": "Videos inspiradores", "description": "Historias de éxito y ejemplos de cómo usar lo aprendido para mejorar tu vida.", "image": "video.svg"},
            {"title": "Glosario profesional", "description": "Términos relacionados con empleo, oficios y educación digital.", "image": "glossary.svg"},
        ],
        "features": [
            {"title": "Crecimiento real", "description": "Secuencias de mejora alineadas con tus necesidades."},
            {"title": "Futuro claro", "description": "Opciones concretas para avanzar en tu desarrollo."},
        ],
    },
    7: {
        "subtitle": "Gestión de tu perfil en el programa.",
        "points": [
            "Verifica tus datos personales y de contacto.",
            "Actualiza tu nombre y contraseña.",
            "Consulta tu estado de activación en el proyecto.",
        ],
        "resources": [
            {"title": "Manual de perfil", "description": "Guía para actualizar datos, revisar tu progreso y administrar tu cuenta.", "image": "guide.svg"},
            {"title": "Infografías de seguimiento", "description": "Visualiza tu avance con esquemas claros y sencillos.", "image": "infographic.svg"},
            {"title": "Cuestionarios de autoevaluación", "description": "Herramientas para medir tu propio desarrollo y fortalecimiento personal.", "image": "quiz.svg"},
            {"title": "Lecturas motivacionales", "description": "Textos breves para acompañar tu proceso de recuperación y crecimiento.", "image": "guide.svg"},
        ],
        "features": [
            {"title": "Seguridad", "description": "Tus datos solo se usan para tu seguimiento."},
            {"title": "Transparencia", "description": "Sabes qué está activo y qué está pendiente."},
        ],
    },
    8: {
        "subtitle": "Instrumentos para administrar el proyecto educativo.",
        "points": [
            "Revisión de usuarios y solicitudes.",
            "Activación de participantes y roles.",
            "Acceso a métricas de avance y uso.",
        ],
        "resources": [
            {"title": "Manuales de administración", "description": "Documentos con procedimientos para gestionar usuarios, permisos y contenidos.", "image": "guide.svg"},
            {"title": "Guías de usuario", "description": "Instrucciones para apoyar a docentes y administradores en su labor diaria.", "image": "guide.svg"},
            {"title": "Artículos de gestión", "description": "Textos sobre mejores prácticas en proyectos educativos y sociales.", "image": "guide.svg"},
            {"title": "Presentaciones de impacto", "description": "Material visual para eventos, reuniones y reportes internos.", "image": "presentation.svg"},
        ],
        "features": [
            {"title": "Administración efectiva", "description": "Solo para el equipo responsable del proyecto."},
            {"title": "Visión del impacto", "description": "Datos útiles para la toma de decisiones."},
        ],
    },
    9: {
        "subtitle": "Actividades y apoyos disponibles según tus necesidades.",
        "points": [
            "Solicita capacitaciones, talleres o proyectos prácticos.",
            "Revisa las actividades de recuperación y empleo.",
            "Elige solo las opciones que aportan a tu progreso.",
        ],
        "resources": [
            {"title": "Videos de actividades", "description": "Lecciones visuales sobre talleres, oficios y dinámicas de recuperación.", "image": "video.svg"},
            {"title": "Cuestionarios de selección", "description": "Pruebas para elegir la actividad que mejor se adapte a tu nivel y metas.", "image": "quiz.svg"},
            {"title": "Guías de solicitud", "description": "Documentos para pedir actividades, explicar requisitos y hacer el seguimiento.", "image": "guide.svg"},
            {"title": "Mapas conceptuales", "description": "Esquemas de la ruta de actividades y de los resultados esperados.", "image": "infographic.svg"},
        ],
        "features": [
            {"title": "Acciones concretas", "description": "Actividades pensadas para tu reenfoque."},
            {"title": "Apoyo pertinente", "description": "Solo se muestra lo que te ayuda a avanzar."},
        ],
    },
}

ROLE_PAGE_NOTES = {
    "admin": "Como administrador, ves el control completo de usuarios, actividades y reportes.",
    "instructor": "Como instructor, enfócate en diseñar talleres, compartir recursos y monitorear el aprendizaje de los estudiantes.",
    "docente": "Como docente, enfócate en el apoyo pedagógico y la gestión de contenidos básicos.",
    "alumno": "Como alumno, revisa tu avance y accede a las oportunidades que te ayuden a crecer.",
    "recuperacion": "Como participante en recuperación, usa este espacio para encontrar apoyo y cursos adaptados.",
}


def find_activity_option(activity_name):
    for item in ACTIVITY_OPTIONS:
        if item["name"] == activity_name:
            return item
    return None


def generate_transfer_ticket(transfer_id):
    return f"TKT-{transfer_id:05d}-{datetime.utcnow().strftime('%Y%m%d')}"


def can_request_activities(user):
    return user and user.get("role") == "recuperacion"


def get_next_sequence(name):
    sequence = db.counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return sequence["sequence_value"]


def init_db():
    db.counters.create_index("sequence_value")
    db.users.create_index("email", unique=True)
    db.users.create_index("id", unique=True)
    db.activity_requests.create_index([("user_id", 1), ("created_at", -1)])
    db.notifications.create_index([("user_id", 1), ("leido", 1), 
                                   ("created_at", -1)])
    db.activity_evidences.create_index([("user_id", 1), ("request_id", 1),
                                         ("created_at", -1)])
    db.cash_transactions.create_index([("user_id", 1), ("created_at", -1)])
    db.action_history.create_index([("user_id", 1), ("created_at", -1)])
    db.loans.create_index([("user_id", 1), ("created_at", -1)])
    db.contact_messages.create_index([("email", 1), ("created_at", -1)])
    db.system_settings.create_index("key", unique=True)
    db.posts.create_index("id", unique=True)
    db.posts.create_index([("fecha", -1)])
    db.instructor_workshops.create_index([("instructor_id", 1), ("date", 1)])
    db.instructor_resources.create_index([("instructor_id", 1), ("created_at", -1)])
    ensure_default_admin()
    ensure_default_instructors()
    ensure_default_demo_users()
    ensure_default_demo_activity_data()
    assign_instructors_to_existing_users()


def ensure_default_admin():
    if not db.users.find_one({"email": "admin@conectayaprende.local"}):
        db.users.insert_one(
            {
                "id": get_next_sequence("users"),
                "nombre": "Administrador",
                "email": "admin@conectayaprende.local",
                "password": generate_password_hash("admin123"),
                "role": "admin",
                "active": True,
                "created_at": datetime.utcnow(),
                "profile_image": None,
            }
        )


def ensure_default_instructors():
    instructors = [
        {
            "nombre": "Laura Silva",
            "email": "laura.silva@instructores.conecta",
            "password": "Instructor2026!",
        },
        {
            "nombre": "Ricardo Méndez",
            "email": "ricardo.mendez@instructores.conecta",
            "password": "Instructor2026!",
        },
        {
            "nombre": "Mariana Torres",
            "email": "mariana.torres@instructores.conecta",
            "password": "Instructor2026!",
        },
        {
            "nombre": "Felipe Gómez",
            "email": "felipe.gomez@instructores.conecta",
            "password": "Instructor2026!",
        },
        {
            "nombre": "Ana Cruz",
            "email": "ana.cruz@instructores.conecta",
            "password": "Instructor2026!",
        },
    ]
    for instructor in instructors:
        if not db.users.find_one({"email": instructor["email"]}):
            db.users.insert_one(
                {
                    "id": get_next_sequence("users"),
                    "nombre": instructor["nombre"],
                    "email": instructor["email"],
                    "password": generate_password_hash(instructor["password"]),
                    "role": "instructor",
                    "active": True,
                    "created_at": datetime.utcnow(),
                    "profile_image": None,
                    "area": "Formación e implementación",
                }
            )


def ensure_default_demo_users():
    demo_users = [
        {
            "nombre": "María Fernández",
            "email": "maria.fernandez@docentes.conecta",
            "password": "Docente2026!",
            "role": "docente",
            "area": "Pedagogía y enseñanza",
            "instructor_email": "laura.silva@instructores.conecta",
            "active": True,
        },
        {
            "nombre": "Carlos Rojas",
            "email": "carlos.rojas@docentes.conecta",
            "password": "Docente2026!",
            "role": "docente",
            "area": "Pedagogía y enseñanza",
            "instructor_email": "ricardo.mendez@instructores.conecta",
            "active": True,
        },
        {
            "nombre": "Ana López",
            "email": "ana.lopez@alumnos.conecta",
            "password": "Alumno2026!",
            "role": "alumno",
            "area": "Oficios y formación",
            "instructor_email": "mariana.torres@instructores.conecta",
            "active": True,
        },
        {
            "nombre": "Jorge Castillo",
            "email": "jorge.castillo@alumnos.conecta",
            "password": "Alumno2026!",
            "role": "alumno",
            "area": "Oficios y formación",
            "instructor_email": "felipe.gomez@instructores.conecta",
            "active": True,
        },
        {
            "nombre": "Mónica Pérez",
            "email": "monica.perez@recuperacion.conecta",
            "password": "Recupera2026!",
            "role": "recuperacion",
            "area": "Reintegración social",
            "instructor_email": "ana.cruz@instructores.conecta",
            "active": True,
        },
        {
            "nombre": "Luis Torres",
            "email": "luis.torres@recuperacion.conecta",
            "password": "Recupera2026!",
            "role": "recuperacion",
            "area": "Reintegración social",
            "instructor_email": "laura.silva@instructores.conecta",
            "active": False,
        },
        {
            "nombre": "Gabriela Díaz",
            "email": "gabriela.diaz@docentes.conecta",
            "password": "DocenteSeguro123!",
            "role": "docente",
            "area": "Pedagogía y enseñanza",
            "instructor_email": "ricardo.mendez@instructores.conecta",
            "active": True,
        },
        {
            "nombre": "Sofía Morales",
            "email": "sofia.morales@alumnos.conecta",
            "password": "AlumnoSeguro123!",
            "role": "alumno",
            "area": "Oficios y formación",
            "instructor_email": "mariana.torres@instructores.conecta",
            "active": True,
        },
        {
            "nombre": "Pablo Gómez",
            "email": "pablo.gomez@recuperacion.conecta",
            "password": "Recupera2026!",
            "role": "recuperacion",
            "area": "Reintegración social",
            "instructor_email": "ana.cruz@instructores.conecta",
            "active": True,
        },
        {
            "nombre": "Laura Mendoza",
            "email": "laura.mendoza@alumnos.conecta",
            "password": "AlumnoSeguro123!",
            "role": "alumno",
            "area": "Oficios y formación",
            "instructor_email": "felipe.gomez@instructores.conecta",
            "active": True,
        },
    ]

    for user in demo_users:
        if db.users.find_one({"email": user["email"]}):
            continue

        instructor_id = None
        if user.get("instructor_email"):
            instructor = db.users.find_one({"email": user["instructor_email"], "role": "instructor"})
            if instructor:
                instructor_id = instructor["id"]

        db.users.insert_one(
            {
                "id": get_next_sequence("users"),
                "nombre": user["nombre"],
                "email": user["email"],
                "password": generate_password_hash(user["password"]),
                "role": user["role"],
                "active": user["active"],
                "created_at": datetime.utcnow(),
                "profile_image": None,
                "area": user["area"],
                "instructor_id": None if user["role"] == "instructor" else instructor_id,
            }
        )


def ensure_default_demo_activity_data():
    demo_workshops = [
        {
            "title": "Taller de sensibilización digital",
            "date": "2026-07-02",
            "modality": "Presencial",
            "group": "Grupo A",
            "description": "Sesión práctica para desarrollar herramientas digitales básicas.",
            "instructor_email": "laura.silva@instructores.conecta",
        },
        {
            "title": "Entrenamiento en redes comunitarias",
            "date": "2026-07-04",
            "modality": "Mixto",
            "group": "Grupo B",
            "description": "Capacitación sobre instalación y mantenimiento de redes.",
            "instructor_email": "ricardo.mendez@instructores.conecta",
        },
        {
            "title": "Proyecto de emprendimiento social",
            "date": "2026-07-08",
            "modality": "En línea",
            "group": "Grupo C",
            "description": "Planificación de una idea de negocio de impacto comunitario.",
            "instructor_email": "mariana.torres@instructores.conecta",
        },
        {
            "title": "Sesión práctica de oficios",
            "date": "2026-07-10",
            "modality": "Presencial",
            "group": "Grupo D",
            "description": "Ejercicios prácticos en herrería y carpintería.",
            "instructor_email": "felipe.gomez@instructores.conecta",
        },
        {
            "title": "Taller de acompañamiento psicosocial",
            "date": "2026-07-12",
            "modality": "En línea",
            "group": "Grupo E",
            "description": "Trabajo en habilidades para la reintegración social.",
            "instructor_email": "ana.cruz@instructores.conecta",
        },
    ]

    for workshop in demo_workshops:
        instructor = db.users.find_one({"email": workshop["instructor_email"], "role": "instructor"})
        if not instructor:
            continue
        if not db.instructor_workshops.find_one({"instructor_id": instructor["id"], "title": workshop["title"]}):
            db.instructor_workshops.insert_one(
                {
                    "id": get_next_sequence("instructor_workshops"),
                    "instructor_id": instructor["id"],
                    "title": workshop["title"],
                    "date": workshop["date"],
                    "modality": workshop["modality"],
                    "group": workshop["group"],
                    "description": workshop["description"],
                    "created_at": datetime.utcnow(),
                }
            )

    demo_resources = [
        {
            "title": "Guía para dinámicas en aula",
            "type": "Guía",
            "link": "https://example.com/guia-dinamicas",
            "notes": "Material para trabajar con grupos mixtos y actividades participativas.",
            "instructor_email": "laura.silva@instructores.conecta",
        },
        {
            "title": "Checklist de seguimiento de participantes",
            "type": "Plantilla",
            "link": "https://example.com/checklist-seguimiento",
            "notes": "Formato para monitorear avances y asistencia.",
            "instructor_email": "ricardo.mendez@instructores.conecta",
        },
        {
            "title": "Plantilla de proyecto social",
            "type": "Plantilla",
            "link": "https://example.com/proyecto-social",
            "notes": "Guía para estructurar ideas de emprendimiento colectivo.",
            "instructor_email": "mariana.torres@instructores.conecta",
        },
        {
            "title": "Manual de herramientas de taller",
            "type": "Manual",
            "link": "https://example.com/manual-taller",
            "notes": "Instrucciones de uso y seguridad para herramientas básicas.",
            "instructor_email": "felipe.gomez@instructores.conecta",
        },
        {
            "title": "Guía de acompañamiento psicosocial",
            "type": "Guía",
            "link": "https://example.com/acompanamiento",
            "notes": "Recursos para trabajar confianza y apoyo emocional.",
            "instructor_email": "ana.cruz@instructores.conecta",
        },
    ]

    for resource in demo_resources:
        instructor = db.users.find_one({"email": resource["instructor_email"], "role": "instructor"})
        if not instructor:
            continue
        if not db.instructor_resources.find_one({"instructor_id": instructor["id"], "title": resource["title"]}):
            db.instructor_resources.insert_one(
                {
                    "id": get_next_sequence("instructor_resources"),
                    "instructor_id": instructor["id"],
                    "title": resource["title"],
                    "type": resource["type"],
                    "link": resource["link"],
                    "notes": resource["notes"],
                    "created_at": datetime.utcnow(),
                }
            )

    demo_requests = [
        {
            "user_email": "monica.perez@recuperacion.conecta",
            "actividad": "Diseño Gráfico",
            "descripcion": "Necesito desarrollar material visual para el taller comunitario.",
            "disponibilidad": "Lunes y Miércoles por la mañana",
            "adicional": "Tengo experiencia básica en pintura.",
            "estado": "aceptado",
            "admin_instructions": "Sigue la guía enviada por correo.",
            "program_notes": "Focalizar en comunicación visual.",
            "meeting_info": "Sesión virtual el 5 de julio a las 10:00.",
            "start_date": "2026-07-05",
            "weekly_plan": "Desarrollar logos y piezas de difusión.",
        },
        {
            "user_email": "luis.torres@recuperacion.conecta",
            "actividad": "Reparación de Herrería",
            "descripcion": "Busco aprender soldadura básica y reparación metálica.",
            "disponibilidad": "Martes y Jueves por la tarde",
            "adicional": "Puedo participar de forma presencial.",
            "estado": "aceptado",
            "admin_instructions": "Trae guantes y protección facial.",
            "program_notes": "Enfocar en prácticas seguras.",
            "meeting_info": "Encuentro en taller el 6 de julio a las 14:00.",
            "start_date": "2026-07-06",
            "weekly_plan": "Introducción a equipos y herramientas.",
        },
    ]

    request_map = {}
    for request in demo_requests:
        user = db.users.find_one({"email": request["user_email"], "role": "recuperacion"})
        if not user:
            continue
        existing = db.activity_requests.find_one({"user_id": user["id"], "actividad": request["actividad"]})
        if existing:
            request_map[user["email"]] = existing["id"]
            continue
        request_id = get_next_sequence("activity_requests")
        db.activity_requests.insert_one(
            {
                "id": request_id,
                "user_id": user["id"],
                "nombre": user["nombre"],
                "email": user["email"],
                "rol": user["role"],
                "actividad": request["actividad"],
                "descripcion": request["descripcion"],
                "disponibilidad": request["disponibilidad"],
                "adicional": request["adicional"],
                "estado": request["estado"],
                "admin_instructions": request["admin_instructions"],
                "program_notes": request["program_notes"],
                "meeting_info": request["meeting_info"],
                "start_date": request["start_date"],
                "weekly_plan": request["weekly_plan"],
                "penalty_dates": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )
        request_map[user["email"]] = request_id

    demo_evidences = [
        {
            "user_email": "monica.perez@recuperacion.conecta",
            "actividad": "Diseño Gráfico",
            "evidencia": "Revisión de bocetos de cartel y línea gráfica inicial.",
            "fecha": "2026-07-07",
        },
        {
            "user_email": "monica.perez@recuperacion.conecta",
            "actividad": "Diseño Gráfico",
            "evidencia": "Presenté dos propuestas de diseño y retroalimentación.",
            "fecha": "2026-07-14",
        },
        {
            "user_email": "luis.torres@recuperacion.conecta",
            "actividad": "Reparación de Herrería",
            "evidencia": "Realicé corte de piezas y ensamble inicial de estructura.",
            "fecha": "2026-07-08",
        },
        {
            "user_email": "luis.torres@recuperacion.conecta",
            "actividad": "Reparación de Herrería",
            "evidencia": "Registré el uso de soldadura con seguridad y limpieza de área.",
            "fecha": "2026-07-15",
        },
    ]

    for evidence in demo_evidences:
        user = db.users.find_one({"email": evidence["user_email"], "role": "recuperacion"})
        if not user:
            continue
        request_id = request_map.get(user["email"])
        if not request_id:
            request_doc = db.activity_requests.find_one({"user_id": user["id"], "actividad": evidence["actividad"]})
            if request_doc:
                request_id = request_doc["id"]
        if not request_id:
            continue
        if db.activity_evidences.find_one({"user_id": user["id"], "request_id": request_id, "evidencia": evidence["evidencia"]}):
            continue
        db.activity_evidences.insert_one(
            {
                "id": get_next_sequence("activity_evidences"),
                "user_id": user["id"],
                "request_id": request_id,
                "evidencia": evidence["evidencia"],
                "image_filename": None,
                "fecha": evidence["fecha"],
                "created_at": datetime.utcnow(),
            }
        )

    demo_cash_transactions = [
        {
            "user_email": "ana.lopez@alumnos.conecta",
            "tipo": "deposito",
            "cantidad": 120.0,
            "estado": "pendiente",
            "referencia": "DEP-00124",
            "comentario": "Solicito depósito para materiales.",
            "actividad": "Taller de sensibilización digital",
        },
        {
            "user_email": "jorge.castillo@alumnos.conecta",
            "tipo": "retiro",
            "cantidad": 80.0,
            "estado": "completado",
            "referencia": "RET-00456",
            "comentario": "Necesito retirar fondos para transporte.",
            "actividad": "Sesión práctica de oficios",
        },
        {
            "user_email": "monica.perez@recuperacion.conecta",
            "tipo": "deposito",
            "cantidad": 150.0,
            "estado": "rechazado",
            "referencia": "DEP-00912",
            "comentario": "Solicitud de pago de actividad de diseño gráfico.",
            "actividad": "Diseño Gráfico",
        },
        {
            "user_email": "pablo.gomez@recuperacion.conecta",
            "tipo": "deposito",
            "cantidad": 100.0,
            "estado": "pendiente",
            "referencia": "DEP-01133",
            "comentario": "Solicitud de depósito para taller de herrería.",
            "actividad": "Reparación de Herrería",
        },
    ]

    for tx in demo_cash_transactions:
        user = db.users.find_one({"email": tx["user_email"]})
        if not user:
            continue
        if db.cash_transactions.find_one({"user_id": user["id"], "referencia": tx["referencia"]}):
            continue
        db.cash_transactions.insert_one(
            {
                "id": get_next_sequence("cash_transactions"),
                "user_id": user["id"],
                "tipo": tx["tipo"],
                "cantidad": tx["cantidad"],
                "estado": tx["estado"],
                "referencia": tx["referencia"],
                "comentario": tx["comentario"],
                "actividad": tx["actividad"],
                "ticket_number": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )

    demo_loans = [
        {
            "user_email": "sofia.morales@alumnos.conecta",
            "cantidad": 200.0,
            "interes": 3.5,
            "plazo_meses": 6,
            "estado": "pendiente",
            "referencia": "LN-2026-001",
            "comentario": "Préstamo para comprar insumos de costura.",
        },
        {
            "user_email": "laura.mendoza@alumnos.conecta",
            "cantidad": 180.0,
            "interes": 4.0,
            "plazo_meses": 5,
            "estado": "aprobado",
            "referencia": "LN-2026-002",
            "comentario": "Necesito apoyo para herramientas de carpintería.",
        },
        {
            "user_email": "luis.torres@recuperacion.conecta",
            "cantidad": 250.0,
            "interes": 5.0,
            "plazo_meses": 8,
            "estado": "rechazado",
            "referencia": "LN-2026-003",
            "comentario": "Solicitud de préstamo para transporte laboral.",
        },
    ]

    for loan in demo_loans:
        user = db.users.find_one({"email": loan["user_email"]})
        if not user:
            continue
        if db.loans.find_one({"user_id": user["id"], "referencia": loan["referencia"]}):
            continue
        db.loans.insert_one(
            {
                "id": get_next_sequence("loans"),
                "user_id": user["id"],
                "cantidad": loan["cantidad"],
                "interes": loan["interes"],
                "plazo_meses": loan["plazo_meses"],
                "estado": loan["estado"],
                "referencia": loan["referencia"],
                "comentario": loan["comentario"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )

    demo_certificates = [
        {
            "user_email": "monica.perez@recuperacion.conecta",
            "actividad": "Diseño Gráfico",
            "titulo": "Certificado por Diseño Gráfico",
            "estado": "pendiente",
            "admin_comments": "Revisión pendiente del área de capacitación.",
            "progress": 100,
        },
        {
            "user_email": "luis.torres@recuperacion.conecta",
            "actividad": "Reparación de Herrería",
            "titulo": "Certificado por Reparación de Herrería",
            "estado": "pendiente",
            "admin_comments": "A la espera de aprobación final.",
            "progress": 100,
        },
    ]

    for cert in demo_certificates:
        user = db.users.find_one({"email": cert["user_email"]})
        if not user:
            continue
        request_doc = db.activity_requests.find_one({"user_id": user["id"], "actividad": cert["actividad"]})
        if not request_doc:
            continue
        if db.certificates.find_one({"user_id": user["id"], "request_id": request_doc["id"], "titulo": cert["titulo"]}):
            continue
        db.certificates.insert_one(
            {
                "id": get_next_sequence("certificates"),
                "user_id": user["id"],
                "request_id": request_doc["id"],
                "titulo": cert["titulo"],
                "estado": cert["estado"],
                "admin_comments": cert["admin_comments"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "awarded_at": None,
                "progress": cert["progress"],
            }
        )

    demo_contact_messages = [
        {
            "user_email": "ana.lopez@alumnos.conecta",
            "subject": "Consulta sobre inscripción",
            "message": "Quisiera saber en qué horario será la siguiente sesión de oficios.",
            "status": "nuevo",
        },
        {
            "user_email": "maria.fernandez@docentes.conecta",
            "subject": "Solicitud de apoyo metodológico",
            "message": "Necesito recomendaciones para la planificación del taller de pedagogía.",
            "status": "nuevo",
        },
        {
            "user_email": "pablo.gomez@recuperacion.conecta",
            "subject": "Problema con acceso a la plataforma",
            "message": "No puedo ver el contenido de mi actividad desde el perfil.",
            "status": "respondido",
            "admin_response": "Estamos revisando el acceso y te avisaremos en breve.",
        },
    ]

    for msg in demo_contact_messages:
        user = db.users.find_one({"email": msg["user_email"]})
        email = msg["user_email"]
        user_id = user["id"] if user else None
        if db.contact_messages.find_one({"email": email, "subject": msg["subject"], "status": msg["status"]}):
            continue
        insert_doc = {
            "user_id": user_id,
            "name": user["nombre"] if user else email,
            "email": email,
            "subject": msg["subject"],
            "message": msg["message"],
            "status": msg["status"],
            "created_at": datetime.utcnow(),
        }
        if msg.get("admin_response"):
            insert_doc["admin_response"] = msg["admin_response"]
            insert_doc["responded_at"] = datetime.utcnow()
        db.contact_messages.insert_one(insert_doc)

    demo_notifications = [
        {
            "user_email": "monica.perez@recuperacion.conecta",
            "titulo": "Actualización de transferencia",
            "mensaje": "Tu solicitud de pago fue recibida y está en revisión.",
        },
        {
            "user_email": "luis.torres@recuperacion.conecta",
            "titulo": "Evaluación de certificado",
            "mensaje": "Tu certificado se encuentra pendiente de aprobación administrativa.",
        },
        {
            "user_email": "sofia.morales@alumnos.conecta",
            "titulo": "Recordatorio de préstamo",
            "mensaje": "Revisa los detalles de tu solicitud de préstamo en el panel.",
        },
    ]

    for note in demo_notifications:
        user = db.users.find_one({"email": note["user_email"]})
        if not user:
            continue
        if db.notifications.find_one({"user_id": user["id"], "titulo": note["titulo"], "mensaje": note["mensaje"]}):
            continue
        db.notifications.insert_one(
            {
                "id": get_next_sequence("notifications"),
                "user_id": user["id"],
                "titulo": note["titulo"],
                "mensaje": note["mensaje"],
                "leido": False,
                "created_at": datetime.utcnow(),
            }
        )


def get_default_area_for_role(role):
    return {
        "docente": "Pedagogía y enseñanza",
        "alumno": "Oficios y formación",
        "recuperacion": "Reintegración social",
        "instructor": "Formación e implementación",
        "admin": "Administración",
    }.get(role, "Apoyo general")


def assign_instructors_to_existing_users():
    instructors = list(db.users.find({"role": "instructor"}))
    if not instructors:
        return

    instructor_load = {
        inst["id"]: db.users.count_documents({"instructor_id": inst["id"]})
        for inst in instructors
    }
    instructor_order = sorted(instructor_load.items(), key=lambda item: (item[1], item[0]))

    for doc in db.users.find({"role": {"$nin": ["admin", "instructor"]}}):
        update_fields = {}
        if not doc.get("area"):
            update_fields["area"] = get_default_area_for_role(doc.get("role"))
        if doc.get("instructor_id") is None:
            assigned_id = instructor_order[0][0]
            update_fields["instructor_id"] = assigned_id
            instructor_order[0] = (instructor_order[0][0], instructor_order[0][1] + 1)
            instructor_order.sort(key=lambda item: (item[1], item[0]))
        if update_fields:
            db.users.update_one({"id": doc["id"]}, {"$set": update_fields})

    for inst in instructors:
        if not inst.get("area"):
            db.users.update_one({"id": inst["id"]}, {"$set": {"area": "Formación e implementación"}})


def assign_instructor_to_user(user_id, role):
    instructor = db.users.find_one({"role": "instructor"}, sort=[("created_at", 1)])
    if not instructor:
        return
    db.users.update_one(
        {"id": user_id},
        {
            "$set": {
                "area": get_default_area_for_role(role),
                "instructor_id": instructor["id"],
            }
        },
    )


def get_instructor_list():
    instructors = []
    for doc in db.users.find({"role": "instructor"}).sort("nombre", 1):
        instructors.append({"id": doc["id"], "nombre": doc["nombre"]})
    return instructors


def get_assigned_students(instructor_id):
    students = []
    for doc in db.users.find({"instructor_id": instructor_id, "role": {"$nin": ["admin", "instructor"]}}).sort("created_at", -1):
        students.append(
            {
                "id": doc["id"],
                "nombre": doc["nombre"],
                "email": doc["email"],
                "role": doc["role"],
                "area": doc.get("area", "Sin área"),
                "created_at": doc.get("created_at"),
            }
        )
    return students


def get_instructor_workshops(instructor_id):
    workshops = []
    for doc in db.instructor_workshops.find({"instructor_id": instructor_id}).sort("date", 1):
        workshops.append(
            {
                "id": doc["id"],
                "title": doc["title"],
                "date": doc.get("date"),
                "modality": doc.get("modality"),
                "group": doc.get("group"),
                "description": doc.get("description"),
                "created_at": doc.get("created_at"),
            }
        )
    return workshops


def get_instructor_resources(instructor_id):
    resources = []
    for doc in db.instructor_resources.find({"instructor_id": instructor_id}).sort("created_at", -1):
        resources.append(
            {
                "id": doc["id"],
                "title": doc["title"],
                "type": doc.get("type", "Recurso"),
                "link": doc.get("link"),
                "notes": doc.get("notes"),
                "created_at": doc.get("created_at"),
            }
        )
    return resources


def get_assigned_evidences(instructor_id):
    students = list(db.users.find({"instructor_id": instructor_id}, {"id": 1}))
    student_ids = [doc["id"] for doc in students]
    if not student_ids:
        return []

    requests = {doc["id"]: doc for doc in db.activity_requests.find({"user_id": {"$in": student_ids}})}
    evidences = []
    for doc in db.activity_evidences.find({"user_id": {"$in": student_ids}}).sort("created_at", -1):
        request_doc = requests.get(doc["request_id"])
        user_doc = db.users.find_one({"id": doc["user_id"]})
        evidences.append(
            {
                "id": doc["id"],
                "student_name": user_doc["nombre"] if user_doc else "Desconocido",
                "student_email": user_doc["email"] if user_doc else "-",
                "activity": request_doc["actividad"] if request_doc else "Actividad desconocida",
                "evidence": doc.get("evidencia", "Sin texto"),
                "image_filename": doc.get("image_filename"),
                "fecha": doc.get("fecha"),
                "created_at": doc.get("created_at"),
            }
        )
    return evidences


def get_instructor_areas(instructor_id):
    areas = set()
    for doc in db.users.find({"instructor_id": instructor_id}):
        if doc.get("area"):
            areas.add(doc["area"])
    return sorted(areas)


def create_user_notification(user_id, titulo, mensaje):
    db.notifications.insert_one(
        {
            "id": get_next_sequence("notifications"),
            "user_id": user_id,
            "titulo": titulo,
            "mensaje": mensaje,
            "leido": False,
            "created_at": datetime.utcnow(),
        }
    )


def get_user_notifications(user_id):
    notifications = []
    for doc in db.notifications.find({"user_id": user_id}).sort("created_at", -1):
        notifications.append(
            (
                doc["id"],
                doc["titulo"],
                doc["mensaje"],
                doc.get("leido", False),
                doc["created_at"],
            )
        )
    return notifications


@app.context_processor
def inject_unread_notifications():
    user_id = session.get("user_id")
    if not user_id:
        return {}
    count = db.notifications.count_documents({"user_id": user_id, "leido": False})
    return {"unread_notifications": count}


@app.context_processor
def inject_current_user():
    return {"user": get_current_user()}


def get_user_activity_request(user_id):
    doc = db.activity_requests.find_one({"user_id": user_id}, sort=[("created_at", -1)])
    if not doc:
        return None
    return {
        "id": doc["id"],
        "actividad": doc["actividad"],
        "descripcion": doc.get("descripcion"),
        "disponibilidad": doc.get("disponibilidad"),
        "adicional": doc.get("adicional"),
        "estado": doc.get("estado", "pendiente"),
        "admin_instructions": doc.get("admin_instructions"),
        "program_notes": doc.get("program_notes"),
        "meeting_info": doc.get("meeting_info"),
        "start_date": doc.get("start_date"),
        "weekly_plan": doc.get("weekly_plan"),
        "penalty_dates": doc.get("penalty_dates", []),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


def parse_activity_start_date(request_data):
    start_date_value = request_data.get("start_date")
    if isinstance(start_date_value, (datetime, date)):
        return start_date_value.date() if isinstance(start_date_value, datetime) else start_date_value
    if isinstance(start_date_value, str) and start_date_value:
        try:
            return datetime.strptime(start_date_value, "%Y-%m-%d").date()
        except ValueError:
            pass
    created_at = request_data.get("created_at")
    if isinstance(created_at, datetime):
        return created_at.date()
    return date.today()


def parse_iso_date(value):
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str) and value:
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            pass
    return None


def get_system_setting(key, default=None):
    setting = db.system_settings.find_one({"key": key})
    return setting["value"] if setting else default


def set_system_setting(key, value):
    if value is None:
        db.system_settings.delete_one({"key": key})
    else:
        db.system_settings.update_one(
            {"key": key},
            {"$set": {"value": value, "updated_at": datetime.utcnow()}},
            upsert=True,
        )


def get_active_date():
    value = get_system_setting("active_date")
    return parse_iso_date(value) if value else None


def get_week_number(start_date, target_date):
    if not start_date or not target_date:
        return 0
    delta_days = (target_date - start_date).days
    if delta_days < 0:
        return 0
    return min(16, delta_days // 7 + 1)


def get_distinct_evidence_weeks(request_data, evidence_entries):
    start_date = parse_activity_start_date(request_data)
    weeks = set()
    for entry in evidence_entries:
        if isinstance(entry, dict):
            fecha = entry.get("fecha")
        else:
            fecha = entry[2] if len(entry) > 2 else None
        entry_date = parse_iso_date(fecha)
        week_number = get_week_number(start_date, entry_date)
        if week_number:
            weeks.add(week_number)
    return weeks


def get_weekly_schedule(request_data):
    default_themes = [
        {"theme": "Bienvenida al programa y responsabilidad diaria", "task": "Registra tu compromiso diario y comparte cómo aplicarás el tema."},
        {"theme": "Comunicación efectiva y respeto en el grupo", "task": "Comparte un ejemplo de comunicación respetuosa que hiciste hoy."},
        {"theme": "Organización del tiempo y entrega de tareas", "task": "Explica cómo te organizaste para cumplir la tarea de hoy."},
        {"theme": "Herramientas básicas y seguridad laboral", "task": "Sube evidencia de los pasos de seguridad que aplicaste."},
        {"theme": "Cuidado personal y bienestar emocional", "task": "Describe una acción de autocuidado realizada hoy."},
        {"theme": "Planificación de metas y seguimiento", "task": "Registra tu meta semanal y el avance de hoy."},
        {"theme": "Trabajo en equipo y apoyo comunitario", "task": "Cuenta cómo colaboraste con otras personas."},
        {"theme": "Salud, alimentación y hábitos positivos", "task": "Sube evidencia de una buena práctica de salud que hiciste."},
        {"theme": "Actitudes para el empleo y responsabilidad", "task": "Describe una actitud responsable que demostraste hoy."},
        {"theme": "Proyecto personal y presentación de avances", "task": "Comparte un avance concreto de tu proyecto."},
        {"theme": "Recursos del municipio y talleres comunitarios", "task": "Anota los datos de la reunión o taller al que asististe."},
        {"theme": "Uso del tiempo libre en actividades productivas", "task": "Explica qué actividad realizaste fuera de la clase para avanzar."},
        {"theme": "Finanzas básicas y administración de apoyos", "task": "Indica cómo registraste o calculaste un gasto del día."},
        {"theme": "Resolución de conflictos y convivencia", "task": "Describe cómo resolviste una situación difícil."},
        {"theme": "Evaluación parcial y ajuste de plan", "task": "Sube tus resultados y qué corregiste hoy."},
        {"theme": "Cierre y preparación de tu certificado", "task": "Comparte tu evidencia final del aprendizaje alcanzado."},
    ]
    plan_lines = []
    if request_data.get("weekly_plan"):
        plan_lines = [line.strip() for line in request_data.get("weekly_plan").splitlines() if line.strip()]
    schedule = []
    for index in range(16):
        if index < len(plan_lines):
            schedule.append(
                {"theme": plan_lines[index], "task": "Sube evidencia diaria relacionada con este tema."}
            )
        else:
            schedule.append(default_themes[index])
    return schedule


def get_program_week(request_data):
    start_date = parse_activity_start_date(request_data)
    today = get_active_date() or date.today()
    elapsed_days = max(0, (today - start_date).days)
    week_number = min(16, elapsed_days // 7 + 1)
    return week_number


def compute_activity_penalty(user_id, request_data, evidence_entries):
    if request_data.get("estado") != "aceptado":
        return {"missing_weeks": 0, "progress_penalty": 0, "cash_penalty": 0}

    current_week = get_program_week(request_data)
    if current_week <= 1:
        return {"missing_weeks": 0, "progress_penalty": 0, "cash_penalty": 0}

    evidence_weeks = get_distinct_evidence_weeks(request_data, evidence_entries)
    missing_weeks = [week for week in range(1, current_week) if week not in evidence_weeks]
    stored_penalties = set(request_data.get("penalty_dates", []))
    new_penalties = [week for week in missing_weeks if str(week) not in stored_penalties]

    if new_penalties:
        for week in new_penalties:
            create_user_notification(
                user_id,
                "Evidencia semanal faltante",
                f"No registraste evidencia en la semana {week}. Se aplicará descuento y reducción de pago.",
            )
            db.cash_transactions.insert_one(
                {
                    "id": get_next_sequence("cash_transactions"),
                    "user_id": user_id,
                    "tipo": "descuento",
                    "cantidad": -20.0,
                    "estado": "aplicado",
                    "referencia": None,
                    "comentario": f"Descuento por falta de evidencia en la semana {week}",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            )
            log_action(
                user_id,
                "penalizacion",
                f"Deducción por evidencia faltante en la semana {week}",
                "activity_request",
                request_data["id"],
            )
        db.activity_requests.update_one(
            {"id": request_data["id"]},
            {
                "$addToSet": {"penalty_dates": {"$each": [str(week) for week in new_penalties]}},
                "$set": {"updated_at": datetime.utcnow()},
            },
        )

    missing_count = len(missing_weeks)
    progress_penalty = min(100, missing_count * 5)
    cash_penalty = missing_count * 20.0
    return {"missing_weeks": missing_count, "progress_penalty": progress_penalty, "cash_penalty": cash_penalty}


def get_learning_progress_bars(request_data, progress):
    if not request_data:
        return {
            "digital_progress": 0,
            "craft_progress": 0,
            "digital_label": "Habilidades Digitales",
            "craft_label": "Curso de Oficios",
        }
    actividad = request_data["actividad"].lower()
    digital_keywords = ["digital", "redes", "internet", "cursos", "tecnología"]
    craft_keywords = ["oficio", "herrería", "carpintería", "costura", "mecánica"]
    digital_progress = 0
    craft_progress = 0
    if any(keyword in actividad for keyword in digital_keywords):
        digital_progress = progress
        craft_progress = max(0, progress - 20)
    elif any(keyword in actividad for keyword in craft_keywords):
        craft_progress = progress
        digital_progress = max(0, progress - 20)
    else:
        digital_progress = progress
        craft_progress = progress
    return {
        "digital_progress": digital_progress,
        "craft_progress": craft_progress,
        "digital_label": "Habilidades Digitales",
        "craft_label": "Curso de Oficios",
    }


def get_user_certificates(user_id):
    certificates = []
    for doc in db.certificates.find({"user_id": user_id}).sort("created_at", -1):
        certificates.append(
            (
                doc["id"],
                doc["titulo"],
                doc.get("estado", "pendiente"),
                doc.get("admin_comments"),
                doc.get("created_at"),
                doc.get("updated_at"),
                doc.get("awarded_at"),
            )
        )
    return certificates


def create_certificate_request_if_eligible(user, request_data, progress):
    if not request_data or request_data.get("estado") != "aceptado":
        return
    if progress < 100:
        return

    request_date = request_data.get("created_at")
    if not request_date or (datetime.utcnow() - request_date).days > 120:
        return

    existing = db.certificates.find_one({
        "user_id": user["id"],
        "request_id": request_data["id"],
        "estado": {"$in": ["pendiente", "aprobado"]},
    })
    if existing:
        return

    titulo = f"Certificado por {request_data['actividad']}"
    db.certificates.insert_one(
        {
            "id": get_next_sequence("certificates"),
            "user_id": user["id"],
            "request_id": request_data["id"],
            "titulo": titulo,
            "estado": "pendiente",
            "admin_comments": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "awarded_at": None,
            "progress": progress,
        }
    )
    create_user_notification(
        user["id"],
        "Certificado pendiente",
        "Has completado el proceso y tu certificado está pendiente de autorización administrativa.",
    )


def get_evidence_entries(user_id, request_id):
    entries = []
    request_data = get_user_activity_request(user_id)
    for doc in db.activity_evidences.find({"user_id": user_id, "request_id": request_id}).sort("created_at", -1):
        evidence_date = parse_iso_date(doc.get("fecha"))
        week_number = get_week_number(parse_activity_start_date(request_data), evidence_date)
        entries.append(
            {
                "id": doc["id"],
                "evidencia": doc.get("evidencia"),
                "fecha": doc.get("fecha"),
                "week": week_number,
                "image_filename": doc.get("image_filename"),
                "created_at": doc.get("created_at"),
            }
        )
    return entries


def get_user_cash_transactions(user_id):
    transactions = []
    for doc in db.cash_transactions.find({"user_id": user_id}).sort("created_at", -1):
        transactions.append(
            (
                doc["id"],
                doc["tipo"],
                doc["cantidad"],
                doc.get("estado", "pendiente"),
                doc.get("referencia"),
                doc.get("comentario"),
                doc.get("actividad"),
                doc.get("ticket_number"),
                doc.get("created_at"),
                doc.get("updated_at"),
            )
        )
    return transactions


def log_action(user_id, action_type, description="", entity_type=None, entity_id=None):
    db.action_history.insert_one(
        {
            "id": get_next_sequence("action_history"),
            "user_id": user_id,
            "action_type": action_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "description": description,
            "created_at": datetime.utcnow(),
        }
    )


def get_user_action_history(user_id):
    entries = []
    for doc in db.action_history.find({"user_id": user_id}).sort("created_at", -1):
        entries.append(
            (
                doc["id"],
                doc["action_type"],
                doc.get("entity_type"),
                doc.get("entity_id"),
                doc.get("description"),
                doc.get("created_at"),
            )
        )
    return entries


def get_all_action_history():
    history = []
    docs = list(db.action_history.find().sort("created_at", -1))
    user_ids = {doc["user_id"] for doc in docs}
    users = {u["id"]: u["nombre"] for u in db.users.find({"id": {"$in": list(user_ids)}})}
    for doc in docs:
        history.append(
            (
                doc["id"],
                users.get(doc["user_id"], "Desconocido"),
                doc["action_type"],
                doc.get("entity_type"),
                doc.get("entity_id"),
                doc.get("description"),
                doc.get("created_at"),
            )
        )
    return history


def get_user_loans(user_id):
    loans = []
    for doc in db.loans.find({"user_id": user_id}).sort("created_at", -1):
        loans.append(
            (
                doc["id"],
                doc["cantidad"],
                doc["interes"],
                doc["plazo_meses"],
                doc.get("estado", "pendiente"),
                doc.get("referencia"),
                doc.get("comentario"),
                doc.get("created_at"),
                doc.get("updated_at"),
            )
        )
    return loans


def get_all_loans():
    loans = []
    docs = list(db.loans.find().sort("created_at", -1))
    user_ids = {doc["user_id"] for doc in docs}
    users = {u["id"]: u["nombre"] for u in db.users.find({"id": {"$in": list(user_ids)}})}
    for doc in docs:
        loans.append(
            (
                doc["id"],
                users.get(doc["user_id"], "Desconocido"),
                doc["cantidad"],
                doc["interes"],
                doc["plazo_meses"],
                doc.get("estado", "pendiente"),
                doc.get("referencia"),
                doc.get("comentario"),
                doc.get("created_at"),
                doc.get("updated_at"),
            )
        )
    return loans


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    doc = db.users.find_one({"id": user_id})
    if not doc:
        return None
    return {
        "id": doc["id"],
        "nombre": doc["nombre"],
        "email": doc["email"],
        "role": doc["role"],
        "active": bool(doc.get("active", False)),
        "created_at": doc.get("created_at"),
        "profile_image": doc.get("profile_image"),
        "area": doc.get("area"),
        "instructor_id": doc.get("instructor_id"),
    }


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


def require_login():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return None


def role_can_access_page(number):
    user = get_current_user()
    if not user:
        return False
    return user["role"] in ROLE_PAGES and number in ROLE_PAGES[user["role"]]


@app.errorhandler(ConnectionError)
def handle_db_connection_error(error):
    return render_template(
        "simple.html",
        title="Error de base de datos",
        subtitle="No se pudo conectar al servidor MongoDB.",
        lines=[str(error)],
        actions=[{"label": "Volver al inicio", "endpoint": "login"}],
    ), 503


db_initialized = False


@app.before_request
def ensure_db_initialized():
    global db_initialized
    if not db_initialized:
        init_db()
        db_initialized = True


@app.route("/")
def home():
    user = get_current_user()
    if not user:
        return render_template(
            "landing.html",
            role_message="Descubre la app Conecta y Aprende y accede a tus herramientas desde aquí.",
        )

    allowed_pages = ROLE_PAGES[user["role"]]
    return render_template(
        "home.html",
        user=user,
        role_label=ROLE_LABELS[user["role"]],
        role_message=ROLE_HOME_MESSAGE.get(user["role"], "Explora tu espacio en la plataforma."),
        allowed_pages=allowed_pages,
        page_titles=PAGE_TITLES,
        page_summaries=PAGE_SUMMARIES,
        role_actions=ROLE_ACTIONS.get(user["role"], [{"label": "Mi Perfil", "endpoint": "profile"}]),
    )


@app.route("/buscar")
def search():
    user = get_current_user()
    query = request.args.get("q", "").strip()
    query_lower = query.lower()
    results = []

    def add_result(title, summary, endpoint, number=None):
        results.append({"title": title, "summary": summary, "endpoint": endpoint, "number": number})

    if query_lower:
        for number in PAGE_TITLES:
            title = PAGE_TITLES.get(number, "")
            summary = PAGE_SUMMARIES.get(number, "")
            if query_lower in title.lower() or query_lower in summary.lower():
                endpoint = "interface_page" if user else "login"
                summary_text = summary if user else f"Inicia sesión para ver {title}."
                add_result(title, summary_text, endpoint, number=number if user else None)
        if user:
            for action in ROLE_ACTIONS.get(user["role"], []):
                label = action["label"]
                if query_lower in label.lower():
                    add_result(label, f"Ir a {label}.", action["endpoint"])
    else:
        for number in ROLE_PAGES.get(user["role"], []) if user else PAGE_TITLES:
            title = PAGE_TITLES.get(number, "")
            summary = PAGE_SUMMARIES.get(number, "")
            endpoint = "interface_page" if user else "login"
            summary_text = summary if user else f"Inicia sesión para ver {title}."
            add_result(title, summary_text, endpoint, number=number if user else None)
        if user:
            for action in ROLE_ACTIONS.get(user["role"], []):
                add_result(action["label"], f"Ir a {action['label']}.", action["endpoint"])

    return render_template("search_results.html", user=user, query=query, results=results)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user_doc = db.users.find_one({"email": email})

        if not user_doc or not check_password_hash(user_doc["password"], password):
            return render_template("login.html", error="Correo o contraseña incorrectos.")
        if not user_doc.get("active", False):
            return render_template("login.html", error="Tu cuenta está pendiente de activación por el administrador.")

        session["user_id"] = user_doc["id"]
        session["role"] = user_doc["role"]
        return redirect(url_for("home"))

    if "user_id" in session:
        return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role")
        password = request.form.get("password", "")

        if not nombre or not email or not password or role not in ROLE_LABELS:
            return render_template("register.html", error="Completa todos los campos correctamente.")

        if role == "instructor":
            return render_template("register.html", error="El registro público no permite crear cuentas de instructor.")

        if db.users.find_one({"email": email}):
            return render_template("register.html", error="Ya existe un usuario con ese correo.")

        user_id = get_next_sequence("users")
        db.users.insert_one(
            {
                "id": user_id,
                "nombre": nombre,
                "email": email,
                "password": generate_password_hash(password),
                "role": role,
                "active": False,
                "created_at": datetime.utcnow(),
                "profile_image": None,
                "area": get_default_area_for_role(role),
            }
        )
        assign_instructor_to_user(user_id, role)

        return render_template(
            "simple.html",
            title="Solicitud enviada",
            subtitle="Hemos recibido tu registro.",
            lines=[
                "Tu cuenta se ha creado en el sistema como solicitud.",
                "El administrador validará tu acceso y te activará la cuenta lo antes posible.",
            ],
            actions=[
                {"label": "Volver al inicio", "endpoint": "login"},
            ],
        )

    return render_template("register.html")


@app.route("/profile")
def profile():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    return render_template("profile.html", user=user)


@app.route("/profile/edit", methods=["GET", "POST"])
def profile_edit():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        password = request.form.get("password", "")
        profile_image = request.files.get("profile_image")

        if not nombre:
            return render_template("profile_edit.html", user=user, error="El nombre no puede estar vacío.")

        update_fields = {"nombre": nombre}
        if password:
            update_fields["password"] = generate_password_hash(password)

        if profile_image and profile_image.filename:
            if not allowed_file(profile_image.filename):
                return render_template("profile_edit.html", user=user, error="Formato de imagen no permitido. Usa png, jpg o gif.")
            filename = secure_filename(profile_image.filename)
            stored_filename = f"profile_{user['id']}_{int(datetime.utcnow().timestamp())}_{filename}"
            profile_image.save(os.path.join(app.config["UPLOAD_FOLDER"], stored_filename))
            update_fields["profile_image"] = stored_filename

        db.users.update_one({"id": user["id"]}, {"$set": update_fields})
        return redirect(url_for("profile"))

    return render_template("profile_edit.html", user=user)


@app.route("/admin/users")
def admin_users():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    instructor_lookup = {
        inst["id"]: inst["nombre"]
        for inst in db.users.find({"role": "instructor"})
    }

    users = []
    for doc in db.users.find().sort("created_at", -1):
        users.append(
            (
                doc["id"],
                doc["nombre"],
                doc["email"],
                doc["role"],
                bool(doc.get("active", False)),
                doc.get("created_at"),
                doc.get("area", ""),
                instructor_lookup.get(doc.get("instructor_id"), "-") if doc.get("instructor_id") else "-",
            )
        )

    return render_template("admin_users.html", users=users)


@app.route("/instructor/panel")
def instructor_dashboard():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "instructor":
        abort(403)

    students_count = db.users.count_documents({"role": {"$in": ["alumno", "docente", "recuperacion"]}})
    accepted_requests = db.activity_requests.count_documents({"estado": "aceptado"})
    evidence_count = db.activity_evidences.count_documents({})

    upcoming_workshops = [
        {
            "title": "Taller de comunicación efectiva",
            "date": "Martes 2 Jul",
            "group": "Grupo A",
            "status": "Planeado",
        },
        {
            "title": "Proyecto de emprendimiento social",
            "date": "Jueves 4 Jul",
            "group": "Grupo B",
            "status": "En curso",
        },
        {
            "title": "Sesión práctica de oficios",
            "date": "Lunes 8 Jul",
            "group": "Grupo C",
            "status": "Confirmado",
        },
    ]

    strategy_tools = [
        {
            "title": "Crear taller nuevo",
            "description": "Define objetivos, recursos y lista de actividades para cada sesión.",
            "endpoint": "actividades_disponibles",
        },
        {
            "title": "Monitorear evidencias",
            "description": "Revisa el progreso de los estudiantes y registra avances semanales.",
            "endpoint": "user_activity_dashboard",
        },
        {
            "title": "Compartir recursos",
            "description": "Organiza materiales, guías y videos para apoyar tus clases.",
            "endpoint": "profile",
        },
    ]

    assigned_students = get_assigned_students(user["id"])
    assigned_student_ids = [student["id"] for student in assigned_students]
    accepted_requests = db.activity_requests.count_documents({"user_id": {"$in": assigned_student_ids}, "estado": "aceptado"}) if assigned_student_ids else 0
    evidence_count = db.activity_evidences.count_documents({"user_id": {"$in": assigned_student_ids}}) if assigned_student_ids else 0
    workshop_count = db.instructor_workshops.count_documents({"instructor_id": user["id"]})
    resource_count = db.instructor_resources.count_documents({"instructor_id": user["id"]})
    assigned_areas = get_instructor_areas(user["id"])

    upcoming_workshops = get_instructor_workshops(user["id"])
    strategy_tools = [
        {
            "title": "Ver estudiantes asignados",
            "description": "Consulta los usuarios bajo tu tutoría y sus áreas de trabajo.",
            "endpoint": "instructor_students",
        },
        {
            "title": "Administrar talleres",
            "description": "Crea y organiza sesiones de formación para tus grupos.",
            "endpoint": "instructor_workshops",
        },
        {
            "title": "Compartir recursos",
            "description": "Suma guías, plantillas y enlaces para apoyar el aprendizaje.",
            "endpoint": "instructor_resources",
        },
    ]

    return render_template(
        "instructor_dashboard.html",
        user=user,
        students_count=len(assigned_students),
        accepted_requests=accepted_requests,
        evidence_count=evidence_count,
        workshop_count=workshop_count,
        resource_count=resource_count,
        assigned_areas=assigned_areas,
        upcoming_workshops=upcoming_workshops,
        strategy_tools=strategy_tools,
    )


@app.route("/instructor/students")
def instructor_students():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "instructor":
        abort(403)

    students = get_assigned_students(user["id"])
    return render_template("instructor_students.html", user=user, students=students)


@app.route("/instructor/workshops")
def instructor_workshops():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "instructor":
        abort(403)

    workshops = get_instructor_workshops(user["id"])
    return render_template("instructor_workshops.html", user=user, workshops=workshops)


@app.route("/instructor/workshops/create", methods=["GET", "POST"])
def instructor_workshop_create():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "instructor":
        abort(403)

    error = None
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        date_value = request.form.get("date", "").strip()
        modality = request.form.get("modality", "").strip()
        group = request.form.get("group", "").strip()
        description = request.form.get("description", "").strip()

        if not title or not date_value or not modality or not group:
            error = "Completa todos los campos obligatorios para crear el taller."
        else:
            db.instructor_workshops.insert_one(
                {
                    "id": get_next_sequence("instructor_workshops"),
                    "instructor_id": user["id"],
                    "title": title,
                    "date": date_value,
                    "modality": modality,
                    "group": group,
                    "description": description,
                    "created_at": datetime.utcnow(),
                }
            )
            return redirect(url_for("instructor_workshops"))

    return render_template("instructor_workshop_form.html", user=user, error=error)


@app.route("/instructor/resources")
def instructor_resources():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "instructor":
        abort(403)

    resources = get_instructor_resources(user["id"])
    return render_template("instructor_resources.html", user=user, resources=resources)


@app.route("/instructor/resources/create", methods=["GET", "POST"])
def instructor_resource_create():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "instructor":
        abort(403)

    error = None
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        resource_type = request.form.get("type", "").strip()
        link = request.form.get("link", "").strip()
        notes = request.form.get("notes", "").strip()

        if not title or not resource_type:
            error = "Completa el título y el tipo de recurso."
        else:
            db.instructor_resources.insert_one(
                {
                    "id": get_next_sequence("instructor_resources"),
                    "instructor_id": user["id"],
                    "title": title,
                    "type": resource_type,
                    "link": link,
                    "notes": notes,
                    "created_at": datetime.utcnow(),
                }
            )
            return redirect(url_for("instructor_resources"))

    return render_template("instructor_resource_form.html", user=user, error=error)


@app.route("/instructor/evidencias")
def instructor_evidences():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "instructor":
        abort(403)

    evidences = get_assigned_evidences(user["id"])
    return render_template("instructor_evidences.html", user=user, evidences=evidences)


@app.route("/admin/assign_instructors")
def admin_assign_instructors():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    assign_instructors_to_existing_users()
    return render_template(
        "simple.html",
        title="Asignaciones actualizadas",
        subtitle="Usuarios y áreas enlazados a instructores correctamente.",
        lines=[
            "Se asignaron instructores a los usuarios existentes.",
            "También se actualizó el campo de área para cada usuario.",
        ],
        actions=[
            {"label": "Volver al panel admin", "endpoint": "admin_users"},
        ],
    )


@app.route("/admin/contact_messages")
def admin_contact_messages():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    messages = []
    for doc in db.contact_messages.find().sort("created_at", -1):
        messages.append(
            {
                "id": str(doc.get("_id")),
                "user_id": doc.get("user_id"),
                "name": doc.get("name", ""),
                "email": doc.get("email", ""),
                "subject": doc.get("subject", "Consulta general"),
                "message": doc.get("message", ""),
                "status": doc.get("status", "nuevo"),
                "created_at": doc.get("created_at"),
                "admin_response": doc.get("admin_response", ""),
            }
        )

    return render_template("admin_contact_messages.html", messages=messages)


@app.route("/admin/contact_messages/<message_id>", methods=["GET", "POST"])
def admin_contact_message_detail(message_id):
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    try:
        message_doc = db.contact_messages.find_one({"_id": ObjectId(message_id)})
    except Exception:
        message_doc = None

    if not message_doc:
        abort(404)

    error = None
    if request.method == "POST":
        response_text = request.form.get("response_text", "").strip()
        status = request.form.get("status", "respondido")

        if not response_text:
            error = "Escribe la respuesta antes de guardar."
        else:
            db.contact_messages.update_one(
                {"_id": message_doc["_id"]},
                {
                    "$set": {
                        "admin_response": response_text,
                        "status": status,
                        "responded_at": datetime.utcnow(),
                    }
                },
            )

            notified_user_id = message_doc.get("user_id")
            if not notified_user_id and message_doc.get("email"):
                matched_user = db.users.find_one({"email": message_doc["email"].lower()})
                if matched_user:
                    notified_user_id = matched_user.get("id")

            if notified_user_id:
                create_user_notification(
                    notified_user_id,
                    "Respuesta a tu mensaje de contacto",
                    f"El administrador respondió tu mensaje: {response_text}",
                )

            flash("Respuesta guardada correctamente.")
            return redirect(url_for("admin_contact_message_detail", message_id=message_id))

    message = {
        "id": str(message_doc.get("_id")),
        "user_id": message_doc.get("user_id"),
        "name": message_doc.get("name", ""),
        "email": message_doc.get("email", ""),
        "subject": message_doc.get("subject", "Consulta general"),
        "message": message_doc.get("message", ""),
        "status": message_doc.get("status", "nuevo"),
        "created_at": message_doc.get("created_at"),
        "admin_response": message_doc.get("admin_response", ""),
        "responded_at": message_doc.get("responded_at"),
    }

    return render_template("admin_contact_message_detail.html", message=message, error=error)


@app.route("/admin/users/create", methods=["GET", "POST"])
def admin_user_create():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    instructors = get_instructor_list()

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role")
        password = request.form.get("password", "")
        active = bool(request.form.get("active"))
        area = request.form.get("area", "").strip()
        instructor_id = request.form.get("instructor_id")

        if not nombre or not email or not password or role not in ROLE_LABELS:
            return render_template("user_form.html", user=None, error="Completa todos los campos.", roles=ROLE_LABELS, instructors=instructors)

        if role == "instructor" and not email.endswith(INSTRUCTOR_EMAIL_SUFFIX):
            return render_template("user_form.html", user=None, error=f"Los instructores deben usar un correo que termine en {INSTRUCTOR_EMAIL_SUFFIX}.", roles=ROLE_LABELS, instructors=instructors)

        if db.users.find_one({"email": email}):
            return render_template("user_form.html", user=None, error="Ya existe un usuario con ese correo.", roles=ROLE_LABELS, instructors=instructors)

        instructor_id_value = None
        if instructor_id and instructor_id.isdigit():
            instructor_id_value = int(instructor_id)
            if not db.users.find_one({"id": instructor_id_value, "role": "instructor"}):
                instructor_id_value = None

        if not area:
            area = get_default_area_for_role(role)

        user_id = get_next_sequence("users")
        db.users.insert_one(
            {
                "id": user_id,
                "nombre": nombre,
                "email": email,
                "password": generate_password_hash(password),
                "role": role,
                "active": active,
                "created_at": datetime.utcnow(),
                "area": area,
                "instructor_id": None if role == "instructor" else instructor_id_value,
            }
        )

        if role != "instructor" and instructor_id_value is None:
            assign_instructor_to_user(user_id, role)

        return redirect(url_for("admin_users"))

    return render_template("user_form.html", user=None, roles=ROLE_LABELS, instructors=instructors)


@app.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
def admin_user_edit(user_id):
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    doc = db.users.find_one({"id": user_id})
    if not doc:
        abort(404)

    target = {
        "id": doc["id"],
        "nombre": doc["nombre"],
        "email": doc["email"],
        "role": doc["role"],
        "active": bool(doc.get("active", False)),
        "area": doc.get("area", ""),
        "instructor_id": doc.get("instructor_id"),
    }

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        role = request.form.get("role")
        active = bool(request.form.get("active"))
        password = request.form.get("password", "")
        area = request.form.get("area", "").strip()
        instructor_id = request.form.get("instructor_id")

        if not nombre or role not in ROLE_LABELS:
            return render_template("user_form.html", user=target, error="Completa todos los campos.", roles=ROLE_LABELS, instructors=get_instructor_list())

        instructor_id_value = None
        if instructor_id and instructor_id.isdigit():
            instructor_id_value = int(instructor_id)
            if not db.users.find_one({"id": instructor_id_value, "role": "instructor"}):
                instructor_id_value = None

        update_fields = {
            "nombre": nombre,
            "role": role,
            "active": active,
            "area": area or get_default_area_for_role(role),
            "instructor_id": None if role == "instructor" else instructor_id_value,
        }
        if password:
            update_fields["password"] = generate_password_hash(password)

        db.users.update_one({"id": user_id}, {"$set": update_fields})

        if role != "instructor" and update_fields["instructor_id"] is None:
            assign_instructor_to_user(user_id, role)

        return redirect(url_for("admin_users"))

    return render_template("user_form.html", user=target, roles=ROLE_LABELS, instructors=get_instructor_list())


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
def admin_user_delete(user_id):
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    db.notifications.delete_many({"user_id": user_id})
    db.activity_requests.delete_many({"user_id": user_id})
    db.activity_evidences.delete_many({"user_id": user_id})
    db.cash_transactions.delete_many({"user_id": user_id})
    db.action_history.delete_many({"user_id": user_id})
    db.loans.delete_many({"user_id": user_id})
    db.users.delete_one({"id": user_id})
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
def admin_user_toggle(user_id):
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    user_doc = db.users.find_one({"id": user_id})
    if user_doc:
        db.users.update_one({"id": user_id}, {"$set": {"active": not user_doc.get("active", False)}})
    return redirect(url_for("admin_users"))


@app.route("/admin/actividades/solicitudes")
def admin_activity_requests():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    requests = []
    for doc in db.activity_requests.find().sort("created_at", -1):
        requests.append(
            (
                doc["id"],
                doc["nombre"],
                doc["email"],
                doc["rol"],
                doc["actividad"],
                doc.get("descripcion"),
                doc.get("disponibilidad"),
                doc.get("adicional"),
                doc.get("estado", "pendiente"),
                doc.get("admin_instructions"),
                doc.get("program_notes"),
                doc.get("meeting_info"),
                doc.get("start_date"),
                doc.get("weekly_plan"),
                doc.get("created_at"),
                doc.get("updated_at"),
            )
        )
    return render_template("admin_activity_requests.html", requests=requests)


@app.route("/admin/fecha-activa", methods=["GET", "POST"])
def admin_active_date():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    active_date = get_active_date()
    if request.method == "POST":
        selected_date = request.form.get("selected_date", "").strip()
        if selected_date:
            try:
                date.fromisoformat(selected_date)
            except ValueError:
                flash("Fecha inválida. Usa el formato AAAA-MM-DD.")
                return redirect(url_for("admin_active_date"))
            set_system_setting("active_date", selected_date)
            log_action(user["id"], "fecha_activa", f"Fecha activa establecida en {selected_date}")
            flash("Fecha activa actualizada.")
        else:
            set_system_setting("active_date", None)
            log_action(user["id"], "fecha_activa", "Fecha activa deshabilitada")
            flash("Fecha activa deshabilitada. Se usará la fecha real del servidor.")
        return redirect(url_for("admin_active_date"))

    return render_template("admin_date_selector.html", active_date=active_date)


@app.route("/admin/actividades/solicitudes/<int:request_id>/procesar", methods=["POST"])
def admin_process_request(request_id):
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    action = request.form.get("action") or request.form.get("action_choice")
    instrucciones = request.form.get("admin_instructions", "").strip()
    program_notes = request.form.get("admin_schedule", "").strip()
    meeting_info = request.form.get("meeting_info", "").strip()
    start_date_value = request.form.get("start_date", "").strip()
    weekly_plan = request.form.get("weekly_plan", "").strip()
    if action not in ["accept", "reject"]:
        flash("No se pudo procesar la solicitud. Intenta de nuevo.")
        return redirect(url_for("admin_activity_requests"))

    nueva_estado = "aceptado" if action == "accept" else "rechazado"
    update_fields = {
        "estado": nueva_estado,
        "admin_instructions": instrucciones,
        "updated_at": datetime.utcnow(),
    }
    if action == "accept":
        update_fields["program_notes"] = program_notes or None
        update_fields["meeting_info"] = meeting_info or None
        update_fields["weekly_plan"] = weekly_plan or None
        if start_date_value:
            update_fields["start_date"] = start_date_value
    db.activity_requests.update_one(
        {"id": request_id},
        {"$set": update_fields},
    )

    request_doc = db.activity_requests.find_one({"id": request_id})
    if request_doc:
        if action == "accept":
            message_body = instrucciones or "Revisa tu panel de actividad para ver los pasos."
            if program_notes:
                message_body += f"\nMaterial y programa: {program_notes}"
            if meeting_info:
                message_body += f"\nReunión programada: {meeting_info}"
            create_user_notification(
                request_doc["user_id"],
                "Solicitud de actividad aceptada",
                message_body,
            )
            flash("Solicitud aceptada correctamente.")
        else:
            create_user_notification(
                request_doc["user_id"],
                "Solicitud de actividad rechazada",
                f"Tu solicitud fue rechazada. {instrucciones or 'Consulta con el administrador.'}",
            )
            flash("Solicitud rechazada correctamente.")

    return redirect(url_for("admin_activity_requests"))


@app.route("/admin/actividades/solicitudes/<int:request_id>/editar", methods=["GET", "POST"])
def admin_activity_request_edit(request_id):
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    doc = db.activity_requests.find_one({"id": request_id})
    if not doc:
        abort(404)

    if request.method == "POST":
        estado = request.form.get("estado", "pendiente")
        descripcion = request.form.get("descripcion", "").strip()
        disponibilidad = request.form.get("disponibilidad", "").strip()
        adicional = request.form.get("adicional", "").strip()
        admin_instructions = request.form.get("admin_instructions", "").strip()
        program_notes = request.form.get("program_notes", "").strip()
        meeting_info = request.form.get("meeting_info", "").strip()
        start_date_value = request.form.get("start_date", "").strip()
        weekly_plan = request.form.get("weekly_plan", "").strip()

        update_fields = {
            "estado": estado,
            "descripcion": descripcion,
            "disponibilidad": disponibilidad,
            "adicional": adicional,
            "admin_instructions": admin_instructions or None,
            "program_notes": program_notes or None,
            "meeting_info": meeting_info or None,
            "weekly_plan": weekly_plan or None,
            "updated_at": datetime.utcnow(),
        }
        if start_date_value:
            update_fields["start_date"] = start_date_value

        db.activity_requests.update_one({"id": request_id}, {"$set": update_fields})
        flash("Solicitud actualizada correctamente.")
        return redirect(url_for("admin_activity_requests"))

    request_data = {
        "id": doc["id"],
        "user_id": doc.get("user_id"),
        "nombre": doc.get("nombre", ""),
        "email": doc.get("email", ""),
        "rol": doc.get("rol", ""),
        "actividad": doc.get("actividad", ""),
        "descripcion": doc.get("descripcion", ""),
        "disponibilidad": doc.get("disponibilidad", ""),
        "adicional": doc.get("adicional", ""),
        "estado": doc.get("estado", "pendiente"),
        "admin_instructions": doc.get("admin_instructions", ""),
        "program_notes": doc.get("program_notes", ""),
        "meeting_info": doc.get("meeting_info", ""),
        "start_date": doc.get("start_date", ""),
        "weekly_plan": doc.get("weekly_plan", ""),
    }
    return render_template("admin_activity_request_edit.html", request_data=request_data)


@app.route("/admin/actividades/solicitudes/<int:request_id>/eliminar", methods=["POST"])
def admin_delete_activity_request(request_id):
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    doc = db.activity_requests.find_one({"id": request_id})
    if doc:
        db.activity_requests.delete_one({"id": request_id})
        create_user_notification(
            doc["user_id"],
            "Solicitud de actividad eliminada",
            "Tu solicitud de actividad ha sido eliminada por el administrador.",
        )
        flash("Solicitud eliminada correctamente.")
    return redirect(url_for("admin_activity_requests"))


@app.route("/admin/transferencias/<int:tx_id>/eliminar", methods=["POST"])
def admin_delete_transfer(tx_id):
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    tx_doc = db.cash_transactions.find_one({"id": tx_id})
    if tx_doc:
        db.cash_transactions.delete_one({"id": tx_id})
        create_user_notification(
            tx_doc["user_id"],
            "Transferencia eliminada",
            "Tu solicitud de transferencia ha sido eliminada por el administrador.",
        )
        flash("Transferencia eliminada correctamente.")
    return redirect(url_for("admin_cash_transfers"))


@app.route("/admin/prestamos/<int:loan_id>/eliminar", methods=["POST"])
def admin_delete_loan(loan_id):
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    loan_doc = db.loans.find_one({"id": loan_id})
    if loan_doc:
        db.loans.delete_one({"id": loan_id})
        create_user_notification(
            loan_doc["user_id"],
            "Solicitud de préstamo eliminada",
            "Tu solicitud de préstamo ha sido eliminada por el administrador.",
        )
        flash("Préstamo eliminado correctamente.")
    return redirect(url_for("admin_loans"))


@app.route("/admin/certificados")
def admin_certificates():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    certificates = []
    docs = list(db.certificates.find().sort("created_at", -1))
    user_ids = {doc["user_id"] for doc in docs}
    users = {u["id"]: u for u in db.users.find({"id": {"$in": list(user_ids)}})}
    for doc in docs:
        user_doc = users.get(doc["user_id"], {})
        certificates.append(
            (
                doc["id"],
                user_doc.get("nombre", "Usuario desconocido"),
                user_doc.get("email", ""),
                doc["titulo"],
                doc.get("estado", "pendiente"),
                doc.get("admin_comments", ""),
                doc.get("created_at"),
            )
        )

    return render_template("admin_certificates.html", certificates=certificates)


@app.route("/admin/certificados/<int:cert_id>/procesar", methods=["POST"])
def admin_process_certificate(cert_id):
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    action = request.form.get("action")
    instrucciones = request.form.get("admin_comments", "").strip()
    if action not in ["approve", "reject"]:
        flash("No se pudo procesar el certificado. Intenta de nuevo.")
        return redirect(url_for("admin_certificates"))

    nueva_estado = "aprobado" if action == "approve" else "rechazado"
    update_fields = {
        "estado": nueva_estado,
        "admin_comments": instrucciones,
        "updated_at": datetime.utcnow(),
    }
    if nueva_estado == "aprobado":
        update_fields["awarded_at"] = datetime.utcnow()

    db.certificates.update_one({"id": cert_id}, {"$set": update_fields})
    cert_doc = db.certificates.find_one({"id": cert_id})
    if cert_doc:
        mensaje = (
            "Tu certificado ha sido autorizado. Podrás verlo en tu lista de certificados."
            if nueva_estado == "aprobado"
            else "Tu certificado ha sido rechazado. Puedes volver a intentar si completas de nuevo tus evidencias."
        )
        create_user_notification(
            cert_doc["user_id"],
            "Actualización de certificado",
            mensaje,
        )
    flash("Certificado procesado correctamente.")
    return redirect(url_for("admin_certificates"))


@app.route("/admin/transferencias")
def admin_cash_transfers():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    transfers = []
    docs = list(db.cash_transactions.find().sort("created_at", -1))
    user_ids = {doc["user_id"] for doc in docs}
    users = {u["id"]: u for u in db.users.find({"id": {"$in": list(user_ids)}})}
    for doc in docs:
        user_doc = users.get(doc["user_id"], {})
        transfers.append(
            (
                doc["id"],
                doc["tipo"],
                doc["cantidad"],
                doc.get("estado", "pendiente"),
                doc.get("referencia"),
                doc.get("comentario"),
                doc.get("actividad"),
                doc.get("ticket_number"),
                doc.get("created_at"),
                doc.get("updated_at"),
                user_doc.get("nombre"),
                user_doc.get("email"),
            )
        )
    return render_template("admin_cash_transfers.html", transfers=transfers)


@app.route("/admin/transferencias/<int:tx_id>/actualizar", methods=["POST"])
def admin_update_transfer(tx_id):
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    nuevo_estado = request.form.get("estado")
    if nuevo_estado not in ["completado", "rechazado"]:
        return redirect(url_for("admin_cash_transfers"))

    comentario = request.form.get("comentario", "").strip()
    db.cash_transactions.update_one(
        {"id": tx_id},
        {"$set": {"estado": nuevo_estado, "comentario": comentario, "updated_at": datetime.utcnow()}},
    )
    tx_doc = db.cash_transactions.find_one({"id": tx_id})
    if tx_doc:
        if nuevo_estado == "completado":
            create_user_notification(tx_doc["user_id"], "Transferencia actualizada", "Tu transferencia ha sido completada.")
        else:
            create_user_notification(tx_doc["user_id"], "Transferencia rechazada", f"Tu transferencia fue rechazada. {comentario or 'Consulta con el administrador.'}")
        log_action(user["id"], f"transferencia_{nuevo_estado}", comentario or f"Transferencia {nuevo_estado}", entity_type="transfer", entity_id=tx_id)
    return redirect(url_for("admin_cash_transfers"))


@app.route("/admin/prestamos")
def admin_loans():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    loans = get_all_loans()
    return render_template("admin_loans.html", loans=loans)


@app.route("/admin/prestamos/<int:loan_id>/actualizar", methods=["POST"])
def admin_update_loan(loan_id):
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    nuevo_estado = request.form.get("estado")
    comentario = request.form.get("comentario", "").strip()
    if nuevo_estado not in ["aprobado", "rechazado", "pagado"]:
        return redirect(url_for("admin_loans"))

    db.loans.update_one(
        {"id": loan_id},
        {"$set": {"estado": nuevo_estado, "comentario": comentario, "updated_at": datetime.utcnow()}},
    )
    loan_doc = db.loans.find_one({"id": loan_id})
    if loan_doc:
        if nuevo_estado == "aprobado":
            create_user_notification(loan_doc["user_id"], "Préstamo aprobado", f"Tu préstamo ha sido aprobado. {comentario or 'Contacta al administrador para recibir los detalles.'}")
        elif nuevo_estado == "rechazado":
            create_user_notification(loan_doc["user_id"], "Préstamo rechazado", f"Tu préstamo fue rechazado. {comentario or 'Consulta con el administrador para más detalles.'}")
        else:
            create_user_notification(loan_doc["user_id"], "Préstamo pagado", "Tu préstamo ha sido marcado como pagado.")
        log_action(user["id"], f"prestamo_{nuevo_estado}", comentario or f"Préstamo {nuevo_estado}", entity_type="loan", entity_id=loan_id)
    return redirect(url_for("admin_loans"))


@app.route("/admin/historial")
def admin_action_history():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    history = get_all_action_history()
    return render_template("admin_action_history.html", history=history)


@app.route("/prestamo/solicitar", methods=["GET", "POST"])
def request_loan():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if request.method == "POST":
        cantidad = request.form.get("cantidad", "").strip()
        interes = request.form.get("interes", "0").strip()
        plazo = request.form.get("plazo", "0").strip()
        referencia = request.form.get("referencia", "").strip()
        motivo = request.form.get("motivo", "").strip()

        if not cantidad or not motivo:
            return render_template(
                "loan_request.html",
                user=user,
                error="Ingresa la cantidad del préstamo y el motivo contractual.",
                cantidad=cantidad,
                interes=interes,
                plazo=plazo,
                referencia=referencia,
                motivo=motivo,
            )

        try:
            cantidad_val = float(cantidad)
            interes_val = float(interes)
            plazo_val = int(plazo)
        except ValueError:
            return render_template(
                "loan_request.html",
                user=user,
                error="Cantidad, interés y plazo deben ser valores numéricos.",
                cantidad=cantidad,
                interes=interes,
                plazo=plazo,
                referencia=referencia,
                motivo=motivo,
            )

        loan_id = get_next_sequence("loans")
        db.loans.insert_one(
            {
                "id": loan_id,
                "user_id": user["id"],
                "cantidad": cantidad_val,
                "interes": interes_val,
                "plazo_meses": plazo_val,
                "estado": "pendiente",
                "referencia": referencia,
                "comentario": motivo,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )
        log_action(user["id"], "solicitud_prestamo", f"Solicitud de préstamo de ${cantidad_val} a {plazo_val} meses.", entity_type="loan", entity_id=loan_id)

        return render_template(
            "simple.html",
            title="Préstamo solicitado",
            subtitle="Tu solicitud de préstamo ha sido registrada.",
            lines=["El administrador revisará tu solicitud y te informará en Mensajes."],
            actions=[{"label": "Mi Actividad", "endpoint": "user_activity_dashboard"}, {"label": "Inicio", "endpoint": "home"}],
        )

    return render_template("loan_request.html", user=user, motivo='')


@app.route("/blog")
def blog_index():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    posts = []
    for doc in db.posts.find().sort("fecha", -1):
        posts.append(
            (
                doc["id"],
                doc["titulo"],
                doc["contenido"],
                doc.get("fecha"),
            )
        )
    return render_template("index.html", posts=posts)


@app.route("/blog/post/<int:id>")
def blog_post(id):
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    doc = db.posts.find_one({"id": id})
    post = None
    if doc:
        post = (doc["id"], doc["titulo"], doc["contenido"], doc.get("fecha"))
    return render_template("post.html", post=post)


@app.route("/blog/create", methods=["GET", "POST"])
def blog_create():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    if request.method == "POST":
        titulo = request.form["titulo"]
        contenido = request.form["contenido"]

        db.posts.insert_one(
            {
                "id": get_next_sequence("posts"),
                "titulo": titulo,
                "contenido": contenido,
                "fecha": datetime.utcnow(),
            }
        )

        return redirect(url_for("blog_index"))

    return render_template("create.html")


@app.route("/interface/<int:number>")
def interface_page(number):
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    if number < 1 or number > 9:
        abort(404)
    if not role_can_access_page(number):
        abort(403)

    user = get_current_user()
    template_name = PAGE_TEMPLATES.get(number)
    if template_name:
        template_context = {"user": user, "can_request": can_request_activities(user)}
        if number == 7:
            request_data = get_user_activity_request(user["id"])
            progress = 0
            if request_data and request_data["estado"] == "aceptado":
                evidence_entries = get_evidence_entries(user["id"], request_data["id"])
                progress = min(100, len(evidence_entries) * 20)
                create_certificate_request_if_eligible(user, request_data, progress)
            else:
                evidence_entries = []
            progress_bars = get_learning_progress_bars(request_data, progress)
            certificate_count = db.certificates.count_documents({"user_id": user["id"], "estado": "aprobado"})
            pending_count = db.certificates.count_documents({"user_id": user["id"], "estado": "pendiente"})
            template_context.update(
                {
                    "progress": progress,
                    "evidence_entries": evidence_entries,
                    "progress_bars": progress_bars,
                    "certificate_count": certificate_count,
                    "pending_certificates": pending_count,
                }
            )
        return render_template(template_name, **template_context)

    page_info = PAGE_INFO.get(number, {})
    page_info = {
        **page_info,
        "title": PAGE_TITLES[number],
        "role_note": ROLE_PAGE_NOTES.get(user["role"], "Usa esta sección según tu perfil."),
        "secondary_action": {
            "label": "Inicio",
            "endpoint": "home",
        },
    }
    return render_template("interface_page.html", user=user, page_info=page_info)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    form_data = {
        "name": user["nombre"] if user else "",
        "email": user["email"] if user else "",
        "subject": "",
        "message": "",
    }
    error = None

    if request.method == "POST":
        form_data = {
            "name": request.form.get("name", "").strip(),
            "email": request.form.get("email", "").strip().lower(),
            "subject": request.form.get("subject", "").strip(),
            "message": request.form.get("message", "").strip(),
        }

        if not form_data["name"] or not form_data["email"] or not form_data["message"]:
            error = "Completa tu nombre, correo y mensaje para enviar tu solicitud."
        else:
            db.contact_messages.insert_one(
                {
                    "user_id": user["id"] if user else None,
                    "name": form_data["name"],
                    "email": form_data["email"],
                    "subject": form_data["subject"] or "Consulta general",
                    "message": form_data["message"],
                    "admin_email": "conectayaprende40@gmail.com",
                    "created_at": datetime.utcnow(),
                    "status": "nuevo",
                }
            )
            flash("Tu mensaje fue enviado correctamente. El administrador lo recibirá pronto.")
            return redirect(url_for("contact"))

    return render_template(
        "contact.html",
        title="Contacto",
        subtitle="Escríbenos para recibir apoyo directo.",
        email="conectayaprende40@gmail.com",
        form_data=form_data,
        error=error,
        actions=[
            {"label": "Volver al inicio", "endpoint": "home"},
        ],
    )


@app.route("/certificados")
def certificados():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    certificates = get_user_certificates(user["id"])
    lines = []
    if not certificates:
        lines = ["No tienes certificados por el momento. Mantén el paso y sube tus evidencias."]
    else:
        for cert in certificates:
            status = cert[2].capitalize()
            created = cert[4].strftime("%Y-%m-%d") if cert[4] else "Fecha desconocida"
            lines.append(f"{cert[1]} — {status} ({created})")

    return render_template(
        "simple.html",
        title="Certificados",
        subtitle=f"Certificados de {user['nombre']}",
        lines=lines,
        actions=[
            {"label": "Ver perfil", "endpoint": "profile"},
            {"label": "Inicio", "endpoint": "home"},
        ],
    )


@app.route("/reportes")
def reportes():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    total_users = db.users.count_documents({})
    active_users = db.users.count_documents({"active": True})
    pending_users = db.users.count_documents({"active": False})
    roles = []
    for doc in db.users.aggregate([
        {"$group": {"_id": "$role", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]):
        roles.append((doc["_id"], doc["count"]))

    lines = [
        f"Usuarios registrados: {total_users}",
        f"Usuarios activos: {active_users}",
        f"Solicitudes pendientes: {pending_users}",
    ]
    for role_name, count in roles:
        lines.append(f"{ROLE_LABELS.get(role_name, role_name)}: {count}")

    return render_template(
        "simple.html",
        title="Reportes Administrativos",
        subtitle="Resumen de actividad y métricas del sistema.",
        lines=lines,
        actions=[
            {"label": "Volver al panel", "endpoint": "admin_users"},
            {"label": "Inicio", "endpoint": "home"},
        ],
    )


@app.route("/solicitar-actividad", methods=["GET", "POST"])
def solicitar_actividad():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if not can_request_activities(user):
        return render_template(
            "simple.html",
            title="Acceso restringido",
            subtitle="No puedes solicitar actividades desde este rol.",
            lines=[
                "El sistema está creado para personas en rehabilitación.",
                "Tu cuenta sigue registrada y visible para el administrador, pero no puede enviar solicitudes de actividad.",
            ],
            actions=[
                {"label": "Inicio", "endpoint": "home"},
                {"label": "Ver actividades", "endpoint": "actividades_disponibles"},
            ],
        )
    if request.method == "POST":
        actividad = request.form.get("actividad", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        disponibilidad = request.form.get("disponibilidad", "").strip()
        adicional = request.form.get("adicional", "").strip()

        if not actividad or not descripcion or not disponibilidad:
            return render_template(
                "activity_request.html",
                user=user,
                role_label=ROLE_LABELS.get(user["role"], user["role"]),
                activities=ACTIVITY_OPTIONS,
                selected_activity=actividad,
                descripcion=descripcion,
                disponibilidad=disponibilidad,
                adicional=adicional,
                error="Completa todos los campos obligatorios para enviar la solicitud.",
            )

        db.activity_requests.insert_one(
            {
                "id": get_next_sequence("activity_requests"),
                "user_id": user["id"],
                "nombre": user["nombre"],
                "email": user["email"],
                "rol": user["role"],
                "actividad": actividad,
                "descripcion": descripcion,
                "disponibilidad": disponibilidad,
                "adicional": adicional,
                "estado": "pendiente",
                "admin_instructions": None,
                "program_notes": None,
                "meeting_info": None,
                "start_date": None,
                "weekly_plan": None,
                "penalty_dates": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )

        return render_template(
            "simple.html",
            title="Solicitud enviada",
            subtitle="Tu solicitud de actividad ha sido registrada.",
            lines=[
                f"Actividad solicitada: {actividad}",
                "Nuestro equipo revisará tu información y te contactará pronto.",
            ],
            actions=[
                {"label": "Volver a Actividades", "endpoint": "actividades_disponibles"},
                {"label": "Inicio", "endpoint": "home"},
            ],
        )

    selected_activity = request.args.get("selected_activity")
    return render_template(
        "activity_request.html",
        user=user,
        role_label=ROLE_LABELS.get(user["role"], user["role"]),
        activities=ACTIVITY_OPTIONS,
        selected_activity=selected_activity,
    )


@app.route("/actividad/pagar/<path:activity_name>", methods=["GET", "POST"])
def pay_activity(activity_name):
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    activity = find_activity_option(activity_name)
    if not activity:
        abort(404)

    if not can_request_activities(user):
        return render_template(
            "simple.html",
            title="Acceso restringido",
            subtitle="No puedes solicitar actividades desde este rol.",
            lines=[
                "El sistema está diseñado para personas en rehabilitación.",
                "Como alumno o docente, puedes navegar y difundir el sistema, pero no solicitar actividades.",
            ],
            actions=[
                {"label": "Inicio", "endpoint": "home"},
                {"label": "Ver actividades", "endpoint": "actividades_disponibles"},
            ],
        )

    if activity["cost"] == 0:
        return redirect(url_for("solicitar_actividad", selected_activity=activity_name))

    error = None
    comentario = None
    if request.method == "POST":
        cantidad = request.form.get("cantidad", "").strip()
        referencia = request.form.get("referencia", "").strip()
        comentario = request.form.get("comentario", "").strip()

        if not cantidad or not referencia:
            error = "Completa la cantidad y la referencia del pago."
        else:
            try:
                cantidad_val = float(cantidad)
            except ValueError:
                error = "La cantidad debe ser numérica."

        if not error:
            if cantidad_val < activity["cost"]:
                error = f"La cantidad debe ser al menos ${activity['cost']}."

        if not error:
            transfer_id = get_next_sequence("cash_transactions")
            db.cash_transactions.insert_one(
                {
                    "id": transfer_id,
                    "user_id": user["id"],
                    "tipo": "deposito",
                    "cantidad": cantidad_val,
                    "estado": "pendiente",
                    "referencia": referencia,
                    "comentario": comentario,
                    "actividad": activity["name"],
                    "ticket_number": None,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            )
            log_action(user["id"], "pago_actividad", f"Solicitud de pago de actividad {activity['name']} de ${cantidad_val}.", entity_type="transfer", entity_id=transfer_id)
            return render_template(
                "simple.html",
                title="Pago registrado",
                subtitle="La solicitud de pago fue enviada al administrador.",
                lines=[
                    f"Actividad: {activity['name']}",
                    f"Cantidad: ${cantidad_val}",
                    "El administrador revisará la transferencia y te enviará un ticket cuando la apruebe.",
                ],
                actions=[
                    {"label": "Mi Actividad", "endpoint": "user_activity_dashboard"},
                    {"label": "Inicio", "endpoint": "home"},
                ],
            )

    return render_template(
        "activity_payment_form.html",
        user=user,
        activity=activity,
        error=error,
        comentario=comentario,
    )


@app.route("/actividades")
def actividades_disponibles():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    free_activities = [item for item in ACTIVITY_OPTIONS if item["cost"] == 0]
    paid_activities = [item for item in ACTIVITY_OPTIONS if item["cost"] > 0]

    return render_template(
        "activity_payment_options.html",
        user=user,
        free_activities=free_activities,
        paid_activities=paid_activities,
        can_request=can_request_activities(user),
    )


@app.route("/actividad")
def user_activity_dashboard():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    can_request = can_request_activities(user)
    request_data = get_user_activity_request(user["id"])
    evidence_entries = []
    cash_transactions = get_user_cash_transactions(user["id"])
    action_history = get_user_action_history(user["id"])
    loans = get_user_loans(user["id"])
    progress = 0
    schedule = []
    current_week = 1
    current_theme = None
    penalty_info = {"missing_weeks": 0, "progress_penalty": 0, "cash_penalty": 0}
    submitted_this_week = False
    if request_data and request_data["estado"] == "aceptado":
        evidence_entries = get_evidence_entries(user["id"], request_data["id"])
        schedule = get_weekly_schedule(request_data)
        current_week = get_program_week(request_data)
        current_theme = schedule[current_week - 1] if current_week <= len(schedule) else {"theme": "Plan completado", "task": "Has finalizado el plan de 16 semanas."}
        evidence_weeks = get_distinct_evidence_weeks(request_data, evidence_entries)
        base_progress = min(100, len(evidence_weeks) * 100.0 / 16.0)
        progress = round(base_progress, 2)
        penalty_info = compute_activity_penalty(user["id"], request_data, evidence_entries)
        submitted_this_week = current_week in evidence_weeks
        create_certificate_request_if_eligible(user, request_data, progress)

    return render_template(
        "activity_dashboard.html",
        user=user,
        request_data=request_data,
        progress=progress,
        evidence_entries=evidence_entries,
        cash_transactions=cash_transactions,
        action_history=action_history,
        loans=loans,
        schedule=schedule,
        current_week=current_week,
        current_theme=current_theme,
        penalty_info=penalty_info,
        submitted_this_week=submitted_this_week,
        can_request=can_request,
    )


@app.route("/actividad/evidencia", methods=["POST"])
def submit_activity_evidence():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    request_data = get_user_activity_request(user["id"])
    if not request_data or request_data["estado"] != "aceptado":
        return render_template(
            "simple.html",
            title="Acceso denegado",
            subtitle="No tienes una actividad activa para subir evidencia.",
            lines=["Solicita una actividad y espera a que el administrador la acepte."],
            actions=[{"label": "Actividades", "endpoint": "actividades_disponibles"}, {"label": "Inicio", "endpoint": "home"}],
        )

    evidencia = request.form.get("evidencia", "").strip()
    image_file = request.files.get("evidence_image")
    if not evidencia and (not image_file or image_file.filename == ""):
        flash("Sube una descripción o una imagen de evidencia para esta semana.")
        return redirect(url_for("user_activity_dashboard"))

    evidence_entries = get_evidence_entries(user["id"], request_data["id"])
    current_week = get_program_week(request_data)
    evidence_weeks = get_distinct_evidence_weeks(request_data, evidence_entries)

    if current_week > 16:
        flash("Tu plan de 16 semanas ha finalizado. No puedes subir más evidencias.")
        return redirect(url_for("user_activity_dashboard"))

    if current_week in evidence_weeks:
        flash("Ya registraste evidencia para esta semana. Espera la próxima semana para subir una nueva evidencia.")
        return redirect(url_for("user_activity_dashboard"))

    image_filename = None
    if image_file and image_file.filename:
        filename = secure_filename(image_file.filename)
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ""
        if ext not in app.config["ALLOWED_EXTENSIONS"]:
            flash("Tipo de imagen no permitido. Usa png, jpg, jpeg o gif.")
            return redirect(url_for("user_activity_dashboard"))
        stored_filename = f"{request_data['id']}_{user['id']}_{int(datetime.utcnow().timestamp())}_{filename}"
        image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], stored_filename))
        image_filename = stored_filename

    evidence_date = get_active_date() or date.today()
    evidence_id = get_next_sequence("activity_evidences")
    db.activity_evidences.insert_one(
        {
            "id": evidence_id,
            "user_id": user["id"],
            "request_id": request_data["id"],
            "evidencia": evidencia,
            "image_filename": image_filename,
            "fecha": evidence_date.isoformat(),
            "created_at": datetime.utcnow(),
        }
    )
    log_action(
        user["id"],
        "evidencia_subida",
        f"Subida de evidencia semanal para solicitud {request_data['id']}",
        entity_type="activity_evidence",
        entity_id=evidence_id,
    )
    flash("Tu evidencia fue registrada. La siguiente carga estará disponible la próxima semana.")
    return redirect(url_for("user_activity_dashboard"))


@app.route("/admin/evidencias")
def admin_evidence_monitor():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    summaries = {}
    for doc in db.activity_evidences.find().sort("created_at", -1):
        user_id = doc["user_id"]
        if user_id not in summaries:
            summaries[user_id] = {
                "user_id": user_id,
                "count": 0,
                "last_date": doc.get("fecha"),
                "last_week": None,
                "activity": None,
                "status": None,
            }
        summaries[user_id]["count"] += 1

    user_ids = list(summaries.keys())
    users = {u["id"]: u for u in db.users.find({"id": {"$in": user_ids}})}
    for user_id, summary in summaries.items():
        user_doc = users.get(user_id, {})
        request_data = get_user_activity_request(user_id)
        summary["name"] = user_doc.get("nombre", "Usuario desconocido")
        summary["email"] = user_doc.get("email", "")
        summary["activity"] = request_data["actividad"] if request_data else "Sin actividad"
        summary["status"] = request_data["estado"] if request_data else "sin solicitud"
        if request_data and summary["last_date"]:
            summary["last_week"] = get_week_number(parse_activity_start_date(request_data), parse_iso_date(summary["last_date"]))

    summaries = sorted(summaries.values(), key=lambda x: x["last_date"] or "", reverse=True)
    return render_template("admin_evidence_monitor.html", summaries=summaries)


@app.route("/admin/usuarios/<int:user_id>/evidencias")
def admin_user_evidence_detail(user_id):
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    if user["role"] != "admin":
        abort(403)

    user_doc = db.users.find_one({"id": user_id})
    if not user_doc:
        abort(404)

    request_data = get_user_activity_request(user_id)
    evidence_entries = []
    for doc in db.activity_evidences.find({"user_id": user_id}).sort("created_at", -1):
        week_number = None
        if request_data and doc.get("fecha"):
            week_number = get_week_number(parse_activity_start_date(request_data), parse_iso_date(doc.get("fecha")))
        evidence_entries.append(
            {
                "id": doc["id"],
                "evidencia": doc.get("evidencia"),
                "fecha": doc.get("fecha"),
                "week": week_number,
                "image_filename": doc.get("image_filename"),
                "created_at": doc.get("created_at"),
            }
        )

    action_history = get_user_action_history(user_id)
    return render_template(
        "admin_user_evidence_detail.html",
        user_info={"id": user_doc["id"], "nombre": user_doc["nombre"], "email": user_doc["email"], "rol": user_doc.get("role", "-")},
        request_data=request_data,
        evidence_entries=evidence_entries,
        action_history=action_history,
    )


@app.route("/depositar-efectivo", methods=["GET", "POST"])
def deposit_cash():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    request_data = get_user_activity_request(user["id"])
    if not request_data or request_data["estado"] != "aceptado":
        return render_template(
            "simple.html",
            title="Acceso denegado",
            subtitle="Solo puedes solicitar depósitos cuando tu actividad está activa.",
            lines=["Espera la aprobación de una solicitud de actividad para utilizar esta función."],
            actions=[{"label": "Mi Actividad", "endpoint": "user_activity_dashboard"}, {"label": "Inicio", "endpoint": "home"}],
        )

    activity = find_activity_option(request_data["actividad"]) or {"name": request_data["actividad"], "cost": 0}
    fixed_amount = activity["cost"]

    if request.method == "POST":
        referencia = request.form.get("referencia", "").strip()
        motivo = request.form.get("motivo", "").strip()

        if not referencia or not motivo:
            return render_template(
                "cash_transaction_form.html",
                user=user,
                tipo="deposito",
                actividad=activity,
                cantidad=fixed_amount,
                error="Completa la referencia y el motivo de la solicitud.",
                referencia=referencia,
                motivo=motivo,
            )

        cantidad_val = fixed_amount

        transfer_id = get_next_sequence("cash_transactions")
        db.cash_transactions.insert_one(
            {
                "id": transfer_id,
                "user_id": user["id"],
                "tipo": "deposito",
                "cantidad": cantidad_val,
                "estado": "pendiente",
                "referencia": referencia,
                "comentario": motivo,
                "actividad": activity["name"],
                "ticket_number": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )
        log_action(user["id"], "transferencia_deposito", f"Solicitud de depósito de ${cantidad_val} para actividad {activity['name']}.", entity_type="transfer", entity_id=transfer_id)
        return render_template(
            "simple.html",
            title="Depósito solicitado",
            subtitle="Tu solicitud de depósito ha sido registrada.",
            lines=[
                f"Actividad: {activity['name']}",
                f"Monto fijo: ${cantidad_val}",
                "El administrador revisará la solicitud y te informará luego.",
            ],
            actions=[{"label": "Mi Actividad", "endpoint": "user_activity_dashboard"}, {"label": "Inicio", "endpoint": "home"}],
        )

    return render_template(
        "cash_transaction_form.html",
        user=user,
        tipo="deposito",
        actividad=activity,
        cantidad=fixed_amount,
    )


@app.route("/retirar-efectivo", methods=["GET", "POST"])
def withdraw_cash():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    request_data = get_user_activity_request(user["id"])
    if not request_data or request_data["estado"] != "aceptado":
        return render_template(
            "simple.html",
            title="Acceso denegado",
            subtitle="Solo puedes solicitar retiro cuando tu actividad está activa.",
            lines=["Espera la aprobación de una solicitud de actividad para utilizar esta función."],
            actions=[{"label": "Mi Actividad", "endpoint": "user_activity_dashboard"}, {"label": "Inicio", "endpoint": "home"}],
        )

    activity = find_activity_option(request_data["actividad"]) or {"name": request_data["actividad"], "cost": 0}
    fixed_amount = activity["cost"]

    if request.method == "POST":
        referencia = request.form.get("referencia", "").strip()
        motivo = request.form.get("motivo", "").strip()

        if not referencia or not motivo:
            return render_template(
                "cash_transaction_form.html",
                user=user,
                tipo="retiro",
                actividad=activity,
                cantidad=fixed_amount,
                error="Completa la referencia y el motivo de la solicitud.",
                referencia=referencia,
                motivo=motivo,
            )

        cantidad_val = fixed_amount

        transfer_id = get_next_sequence("cash_transactions")
        db.cash_transactions.insert_one(
            {
                "id": transfer_id,
                "user_id": user["id"],
                "tipo": "retiro",
                "cantidad": cantidad_val,
                "estado": "pendiente",
                "referencia": referencia,
                "comentario": motivo,
                "actividad": activity["name"],
                "ticket_number": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )
        log_action(user["id"], "transferencia_retiro", f"Solicitud de retiro de ${cantidad_val} para actividad {activity['name']}.", entity_type="transfer", entity_id=transfer_id)
        return render_template(
            "simple.html",
            title="Retiro solicitado",
            subtitle="Tu solicitud de retiro ha sido registrada.",
            lines=[
                f"Actividad: {activity['name']}",
                f"Monto fijo: ${cantidad_val}",
                "El administrador evaluará la solicitud y te informará mediante Mensajes.",
            ],
            actions=[{"label": "Mi Actividad", "endpoint": "user_activity_dashboard"}, {"label": "Inicio", "endpoint": "home"}],
        )

    return render_template(
        "cash_transaction_form.html",
        user=user,
        tipo="retiro",
        actividad=activity,
        cantidad=fixed_amount,
    )


@app.route("/mensajes")
def user_notifications():
    redirect_to_login = require_login()
    if redirect_to_login:
        return redirect_to_login

    user = get_current_user()
    notifications = get_user_notifications(user["id"])
    db.notifications.update_many({"user_id": user["id"]}, {"$set": {"leido": True}})
    return render_template("notifications.html", user=user, notifications=notifications)


@app.errorhandler(403)
def forbidden(error):
    return render_template(
        "simple.html",
        title="Acceso denegado",
        subtitle="No tienes permiso para acceder a esta sección.",
        lines=[
            "Esta funcionalidad es sólo para usuarios con el rol adecuado.",
            "Si crees que es un error, contacta al administrador.",
        ],
        actions=[
            {"label": "Inicio", "endpoint": "home"},
        ],
    ), 403


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
