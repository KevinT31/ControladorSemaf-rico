"""Visión para NSB (F4, spec §15-§17): SOLO fuente ADVISORY.

Reutiliza el pipeline YOLO+tracking existente (``vision_computadora/``) sin
modificarlo. cv2/ultralytics se importan perezosamente: este paquete importa
en cualquier plataforma (la Pi base no trae visión — spec §37).
"""
