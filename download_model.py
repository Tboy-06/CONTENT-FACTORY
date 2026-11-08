import os
import shutil
from huggingface_hub import hf_hub_download

model_repo = 'bartowski/Llama-3.2-3B-Instruct-GGUF'
filename = 'Llama-3.2-3B-Instruct-Q4_K_M.gguf'

target_dir_1 = r'D:\CONTENT-FACTORY\backend\models'
target_dir_2 = 'D:\\\\'

os.makedirs(target_dir_1, exist_ok=True)

print('Downloading model to backend folder...')
local_path = hf_hub_download(repo_id=model_repo, filename=filename, local_dir=target_dir_1)
print(f'Downloaded to {local_path}')

print(f'Copying to root D:\ ...')
shutil.copy(local_path, os.path.join(target_dir_2, filename))
print('Complete!')
