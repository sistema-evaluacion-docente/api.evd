"""
Script para probar los modelos de IA de forma local.
Uso: python test_ai_models.py
"""

from dotenv import load_dotenv
load_dotenv()

import os
from transformers import pipeline

RISK_MODEL = os.getenv("HUGGINGFACE_RISK_MODEL")
CATEGORY_MODEL = os.getenv("HUGGINGFACE_CATEGORY_MODEL")

COMENTARIOS_PRUEBA = [
    "El profesor explica muy bien y siempre está disponible para resolver dudas.",
    "El profesor nunca llegaba a tiempo y no respondía las preguntas en clase.",
    "Este profesor tiene actitudes irrespetuosas hacia los estudiantes.",
]


def main():
    print(f"Modelo de riesgo:    {RISK_MODEL}")
    print(f"Modelo de categoría: {CATEGORY_MODEL}")
    print()

    print("Cargando modelo de riesgo...")
    risk_pipe = pipeline("text-classification", model=RISK_MODEL)
    print("✅ Modelo de riesgo cargado")
    print()

    print("Cargando modelo de categoría...")
    category_pipe = pipeline("text-classification", model=CATEGORY_MODEL)
    print("✅ Modelo de categoría cargado")
    print()

    for comentario in COMENTARIOS_PRUEBA:
        print("=" * 60)
        print(f"Comentario: {comentario}")
        print()

        risk_result = risk_pipe(comentario)
        print(f"Riesgo     → label: {risk_result[0]['label']}  |  score: {risk_result[0]['score']:.4f}")
        print(f"Raw: {risk_result}")

        print()

        category_result = category_pipe(comentario)
        print(f"Categoría  → label: {category_result[0]['label']}  |  score: {category_result[0]['score']:.4f}")
        print(f"Raw: {category_result}")
        print()


if __name__ == "__main__":
    main()
