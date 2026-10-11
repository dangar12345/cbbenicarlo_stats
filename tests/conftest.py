import os
import sys

# Ejecutar pytest desde la raíz del proyecto sin instalar el paquete
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
