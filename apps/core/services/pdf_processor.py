import hashlib
import io
import pypdf
from django.core.exceptions import ValidationError
from sentence_transformers import SentenceTransformer

# Cargador perezoso para el modelo sentence-transformers (768 dimensiones) (RF-2.3)
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
    return _embedding_model


def procesar_pdf_en_memoria(file_obj, chunk_size=1000, overlap=150):
    """
    Lee el PDF en memoria, genera su hash SHA-256 y extrae fragmentos de texto (RF-2.2).
    """
    file_bytes = file_obj.read()
    
    # Calculo del Hash SHA-256 del PDF completo
    hash_documento = hashlib.sha256(file_bytes).hexdigest()

    # Lectura del contenido sin escribir en el almacenamiento físico
    try:
        pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        paginas_texto = []
        for page in pdf_reader.pages:
            texto = page.extract_text()
            if texto:
                paginas_texto.append(texto)
        texto_completo = "\n".join(paginas_texto)
    except Exception as e:
        raise ValidationError(f"Error al leer la estructura del archivo PDF: {str(e)}")

    if not texto_completo.strip():
        raise ValidationError("El archivo PDF no contiene texto legible o es un documento escaneado como imagen.")

    # Chunking / Fragmentación
    chunks = []
    start = 0
    longitud_texto = len(texto_completo)

    while start < longitud_texto:
        end = start + chunk_size
        chunk = texto_completo[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += (chunk_size - overlap)

    return hash_documento, chunks


def generar_vector_embedding(texto):
    """
    Genera el vector embedding localmente usando sentence-transformers (RF-2.3).
    """
    model = get_embedding_model()
    embedding = model.encode(texto, convert_to_numpy=True)
    return embedding.tolist()


def calcular_hash_fragmento(texto):
    """
    Genera un hash SHA-256 del contenido del fragmento.
    """
    return hashlib.sha256(texto.encode('utf-8')).hexdigest()