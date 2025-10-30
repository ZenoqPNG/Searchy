import os
import re

class SearchEngine:
    def __init__(self, scan_paths):
        self.scan_paths = scan_paths
        self.file_list = []

    def scan_files(self, progress_callback=None, live_update_callback=None):
        self.file_list = []
        for folder in self.scan_paths:
            if os.path.exists(folder):
                for root_dir, dirs, files in os.walk(folder):
                    for file in files:
                        path = os.path.join(root_dir, file)
                        self.file_list.append((file, path))
                        if live_update_callback:
                            live_update_callback(self.file_list)
                    for dir_name in dirs:
                        path = os.path.join(root_dir, dir_name)
                        self.file_list.append((dir_name, path))
                        if live_update_callback:
                            live_update_callback(self.file_list)
        return self.file_list

    def parse_smart_search(self, query):
        filters = {}
        name_match = re.search(r'nom:(\w+)', query)
        if name_match:
            filters['name'] = name_match.group(1)
            query = re.sub(r'nom:\w+', '', query).strip()
        type_match = re.search(r'type:(\.\w+)', query)
        if type_match:
            filters['extension'] = type_match.group(1)
            query = re.sub(r'type:\.\w+', '', query).strip()
        size_match = re.search(r'taille([><=])(\d+)', query)
        if size_match:
            op, size = size_match.groups()
            if op == '>':
                filters['min_size'] = size
            elif op == '<':
                filters['max_size'] = size
            query = re.sub(r'taille[><=]\d+', '', query).strip()
        filters['keyword'] = query
        return filters

    def search_files(self, filters, content_search=False):
        keyword = filters.get('keyword', '').lower()
        results = []
        for name, path in self.file_list:
            match = True
            if keyword and keyword not in name.lower():
                match = False
            if 'name' in filters and filters['name'].lower() not in name.lower():
                match = False
            if 'extension' in filters and not name.lower().endswith(filters['extension'].lower()):
                match = False
            if 'min_size' in filters and os.path.isfile(path):
                if os.path.getsize(path) < int(filters['min_size']) * 1024:
                    match = False
            if 'max_size' in filters and os.path.isfile(path):
                if os.path.getsize(path) > int(filters['max_size']) * 1024:
                    match = False
            if content_search and os.path.isfile(path) and path.lower().endswith(('.txt','.py','.md','.html','.css','.js')):
                try:
                    with open(path,'r',encoding='utf-8', errors='ignore') as f:
                        if keyword not in f.read().lower():
                            match = False
                except:
                    match = False
            if match:
                results.append((name, path))
        return results
