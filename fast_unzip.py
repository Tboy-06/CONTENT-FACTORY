import zipfile; print('Extracting...'); z=zipfile.ZipFile('ollama.zip', 'r'); z.extractall('ollama_bin'); z.close(); print('Done!')
