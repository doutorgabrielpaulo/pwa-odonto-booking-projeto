# booking/app/utils.py
import re

def get_youtube_id(url):
    """
    Extrai o ID de um vídeo do YouTube a partir de uma URL
    Exemplo: 
        Input: https://www.youtube.com/watch?v=abc123
        Output: abc123
    """
    if not url:
        return None
        
    # Padrões regex para diferentes formatos de URL do YouTube
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',  # Padrão para URLs como ?v=ID ou /ID
        r'(?:embed\/)([0-9A-Za-z_-]{11})',   # Padrão para embed
        r'(?:watch\?v=)([0-9A-Za-z_-]{11})'  # Padrão para watch
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None
