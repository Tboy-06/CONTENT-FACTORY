import urllib.request
import zipfile
print('Downloading...')
urllib.request.urlretrieve('https://github.com/ollama/ollama/releases/latest/download/ollama-windows-amd64.zip', 'ollama.zip')
print('Extracting...')
with zipfile.ZipFile('ollama.zip', 'r') as z:
    z.extractall('ollama_bin')
print('Done!')
