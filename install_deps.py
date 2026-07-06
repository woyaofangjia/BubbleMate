import urllib.request
import os
import sys
import subprocess

def install_package(pkg_name):
    print(f'Installing {pkg_name}...')
    try:
        import importlib
        importlib.import_module(pkg_name)
        print(f'{pkg_name} is already installed')
        return True
    except ImportError:
        pass
    
    url = f'https://pypi.tuna.tsinghua.edu.cn/simple/{pkg_name}/'
    try:
        with urllib.request.urlopen(url) as f:
            content = f.read().decode()
        
        whl_files = []
        for line in content.split('\n'):
            if '.whl' in line and 'cp313' in line:
                idx = line.find('href="')
                if idx != -1:
                    end_idx = line.find('"', idx + 6)
                    if end_idx != -1:
                        whl_files.append(line[idx + 6:end_idx])
        
        if whl_files:
            whl_url = 'https://pypi.tuna.tsinghua.edu.cn' + whl_files[0]
            print(f'Downloading {whl_url}')
            whl_path = os.path.join(os.path.expanduser('~'), 'Downloads', os.path.basename(whl_url))
            urllib.request.urlretrieve(whl_url, whl_path)
            print(f'Installing from {whl_path}')
            
            subprocess.run([sys.executable, '-m', 'pip', 'install', whl_path], check=True)
            print(f'{pkg_name} installed successfully')
            return True
        else:
            print(f'No whl file found for {pkg_name}')
            return False
    except Exception as e:
        print(f'Failed to install {pkg_name}: {e}')
        return False

if __name__ == '__main__':
    packages = ['python-dotenv', 'requests', 'zhipuai']
    for pkg in packages:
        install_package(pkg)